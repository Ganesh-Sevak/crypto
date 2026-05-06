import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .cache import Cache
from .config import get_settings
from .logging_config import configure_logging
from .metrics import MetricsCalculator
from .models import PriceAlertRequest, SYMBOLS
from .price_alerts import PriceAlertStore
from .risk import RiskEngine
from .sms import SmsClient
from .stream import CoinbaseMarketDataProvider, stream_ticks

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


class AppState:
    def __init__(self) -> None:
        self.cache = Cache(settings.redis_url)
        self.metrics = MetricsCalculator(settings.price_window_size)
        self.risk = RiskEngine(settings.risk)
        self.price_alerts = PriceAlertStore()
        self.sms = SmsClient(settings)
        self.live_market = CoinbaseMarketDataProvider(settings.live_market_base_url)
        self.latest: dict[str, dict] = {}
        self.clients: set[WebSocket] = set()
        self.task: asyncio.Task | None = None


state = AppState()


async def broadcast(payload: dict) -> None:
    disconnected: list[WebSocket] = []
    for client in state.clients:
        try:
            await client.send_json(payload)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        state.clients.discard(client)


async def market_loop() -> None:
    async for tick in stream_ticks(settings.stream_interval_seconds, settings.market_data_source, settings.live_market_base_url):
        try:
            metric = state.metrics.update(tick)
            alerts = state.risk.evaluate(metric)
            state.latest[tick.symbol] = metric.model_dump(mode="json")
            await state.cache.set_metric(tick.symbol, metric)
            if alerts:
                await state.cache.push_alerts(alerts)
            sms_alerts = state.price_alerts.evaluate(metric)
            for subscription in sms_alerts:
                try:
                    await state.sms.send_price_alert(subscription)
                except Exception:
                    logger.exception("Failed to send SMS price alert")
            await broadcast(
                {
                    "type": "market_update",
                    "tick": tick.model_dump(mode="json"),
                    "metric": metric.model_dump(mode="json"),
                    "alerts": [alert.model_dump(mode="json") for alert in alerts],
                    "sms_alerts": [subscription.model_dump(mode="json") for subscription in sms_alerts],
                }
            )
        except Exception:
            logger.exception("Failed to process market tick")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await state.cache.connect()
    state.task = asyncio.create_task(market_loop())
    logger.info("Market stream started")
    try:
        yield
    finally:
        if state.task:
            state.task.cancel()
        await state.cache.close()
        logger.info("Market stream stopped")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "symbols": SYMBOLS, "cache": "redis" if state.cache.client else "memory"}


@app.get("/symbols")
async def symbols() -> list[str]:
    return SYMBOLS


@app.get("/market-data/source")
async def market_data_source() -> dict:
    return {
        "stream_source": settings.market_data_source,
        "live_provider": "coinbase",
        "live_base_url": settings.live_market_base_url,
    }


@app.get("/market-data/live/{symbol}")
async def live_market_data(symbol: str) -> dict:
    if symbol not in SYMBOLS:
        raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
    try:
        tick = await state.live_market.fetch_tick(symbol)
    except Exception as exc:
        logger.exception("Failed to fetch live market data")
        raise HTTPException(status_code=502, detail="Live market data provider unavailable") from exc
    return tick.model_dump(mode="json")


@app.get("/metrics")
async def metrics() -> dict:
    cached = await state.cache.get_metrics()
    return cached or state.latest


@app.get("/alerts")
async def alerts() -> list:
    return await state.cache.get_alerts()


@app.get("/sms/price-alerts")
async def list_price_alerts() -> list:
    return [subscription.model_dump(mode="json") for subscription in state.price_alerts.list()]


@app.post("/sms/price-alerts")
async def create_price_alert(request: PriceAlertRequest) -> dict:
    if request.symbol not in SYMBOLS:
        raise HTTPException(status_code=400, detail=f"Unsupported symbol: {request.symbol}")
    subscription = state.price_alerts.add(request)
    return {
        "subscription": subscription.model_dump(mode="json"),
        "sms_mode": "twilio" if state.sms.enabled else "dry_run",
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    state.clients.add(websocket)
    try:
        await websocket.send_json({"type": "snapshot", "metrics": await metrics(), "alerts": await alerts()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.clients.discard(websocket)
    except Exception:
        state.clients.discard(websocket)
        logger.exception("WebSocket client error")
