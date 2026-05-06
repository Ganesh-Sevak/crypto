import asyncio
import logging
import random
from datetime import datetime, timezone

import httpx

from .models import MarketTick, SYMBOLS

logger = logging.getLogger(__name__)


class MarketDataSimulator:
    def __init__(self) -> None:
        self.state = {
            "BTC-USD": {"price": 68100.0, "base_volume": 18.0},
            "ETH-USD": {"price": 3425.0, "base_volume": 80.0},
            "SOL-USD": {"price": 148.0, "base_volume": 420.0},
        }

    def next_tick(self, symbol: str) -> MarketTick:
        state = self.state[symbol]
        shock = random.gauss(0, 0.0018)
        if random.random() < 0.025:
            shock += random.choice([-1, 1]) * random.uniform(0.006, 0.018)
        price = max(0.01, state["price"] * (1 + shock))
        state["price"] = price

        spread_ratio = random.uniform(0.0002, 0.002)
        if random.random() < 0.04:
            spread_ratio *= random.uniform(2.5, 5.0)
        half_spread = price * spread_ratio / 2
        bid_size = max(1.0, random.gauss(state["base_volume"], state["base_volume"] * 0.35))
        ask_size = max(1.0, random.gauss(state["base_volume"], state["base_volume"] * 0.35))
        if random.random() < 0.04:
            bid_size *= random.uniform(0.1, 0.3)
        if random.random() < 0.04:
            ask_size *= random.uniform(0.1, 0.3)

        return MarketTick(
            symbol=symbol,
            price=round(price, 2),
            bid=round(price - half_spread, 2),
            ask=round(price + half_spread, 2),
            bid_size=round(bid_size, 2),
            ask_size=round(ask_size, 2),
            volume=round(random.uniform(0.5, 2.2) * state["base_volume"], 2),
            source="simulated",
            timestamp=datetime.now(timezone.utc),
        )


class CoinbaseMarketDataProvider:
    def __init__(self, base_url: str = "https://api.exchange.coinbase.com") -> None:
        self.base_url = base_url.rstrip("/")

    async def fetch_tick(self, symbol: str) -> MarketTick:
        url = f"{self.base_url}/products/{symbol}/ticker"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            return self.tick_from_payload(symbol, response.json())

    def tick_from_payload(self, symbol: str, payload: dict) -> MarketTick:
        timestamp_text = payload.get("time")
        timestamp = datetime.now(timezone.utc)
        if timestamp_text:
            timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))

        price = float(payload["price"])
        bid = float(payload.get("bid") or price)
        ask = float(payload.get("ask") or price)
        size = max(float(payload.get("size") or 1.0), 0.000001)
        volume = max(float(payload.get("volume") or size), size)

        return MarketTick(
            symbol=symbol,
            price=round(price, 2),
            bid=round(bid, 2),
            ask=round(ask, 2),
            bid_size=round(size, 8),
            ask_size=round(size, 8),
            volume=round(volume, 8),
            source="coinbase",
            timestamp=timestamp,
        )


async def stream_ticks(interval_seconds: float, source: str = "simulated", live_base_url: str = "https://api.exchange.coinbase.com"):
    simulator = MarketDataSimulator()
    live_provider = CoinbaseMarketDataProvider(live_base_url)
    while True:
        for symbol in SYMBOLS:
            if source == "live":
                try:
                    yield await live_provider.fetch_tick(symbol)
                    continue
                except Exception:
                    logger.warning("Live market data unavailable; falling back to simulated tick", exc_info=True)
            yield simulator.next_tick(symbol)
        await asyncio.sleep(interval_seconds)
