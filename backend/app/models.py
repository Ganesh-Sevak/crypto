from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD"]


class MarketTick(BaseModel):
    symbol: str
    price: float
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    volume: float
    source: str = "simulated"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetricSnapshot(BaseModel):
    symbol: str
    price: float
    volatility: float
    spread: float
    spread_bps: float
    vwap: float
    rolling_price_change: float
    liquidity_score: float
    volume_imbalance: float
    source: str = "simulated"
    timestamp: datetime


class Alert(BaseModel):
    id: str
    symbol: str
    severity: str
    type: str
    message: str
    value: float
    threshold: float
    timestamp: datetime


class PriceAlertRequest(BaseModel):
    phone_number: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    symbol: str
    direction: Literal["above", "below"]
    target_price: float = Field(gt=0)


class PriceAlertSubscription(BaseModel):
    id: str
    phone_number: str
    symbol: str
    direction: Literal["above", "below"]
    target_price: float
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    triggered_at: datetime | None = None
    last_price: float | None = None
