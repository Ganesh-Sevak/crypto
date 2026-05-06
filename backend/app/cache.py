import json
import logging
from collections import deque
from typing import Any

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover
    redis = None

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.client: Any = None
        self.memory: dict[str, Any] = {"metrics": {}, "alerts": deque(maxlen=100)}

    async def connect(self) -> None:
        if redis is None:
            logger.warning("Redis package unavailable; using in-memory cache")
            return
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            await self.client.ping()
            logger.info("Connected to Redis cache")
        except Exception:
            logger.warning("Redis unavailable; using in-memory cache", exc_info=True)
            self.client = None

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()

    async def set_metric(self, symbol: str, metric: BaseModel) -> None:
        payload = metric.model_dump_json()
        self.memory["metrics"][symbol] = json.loads(payload)
        if self.client:
            await self.client.hset("metrics", symbol, payload)

    async def get_metrics(self) -> dict[str, Any]:
        if self.client:
            data = await self.client.hgetall("metrics")
            return {symbol: json.loads(payload) for symbol, payload in data.items()}
        return self.memory["metrics"]

    async def push_alerts(self, alerts: list[BaseModel]) -> None:
        for alert in alerts:
            payload = alert.model_dump_json()
            self.memory["alerts"].appendleft(json.loads(payload))
            if self.client:
                await self.client.lpush("alerts", payload)
                await self.client.ltrim("alerts", 0, 99)

    async def get_alerts(self) -> list[Any]:
        if self.client:
            return [json.loads(item) for item in await self.client.lrange("alerts", 0, 99)]
        return list(self.memory["alerts"])
