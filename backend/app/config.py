from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RiskThresholds(BaseModel):
    high_volatility: float = 0.018
    wide_spread: float = 0.0035
    low_liquidity: float = 35.0
    volume_imbalance: float = 0.55


class Settings(BaseSettings):
    app_name: str = "Crypto Market Risk & Liquidity Monitoring System"
    redis_url: str = "redis://localhost:6379/0"
    market_data_source: Literal["simulated", "live"] = "simulated"
    live_market_base_url: str = "https://api.exchange.coinbase.com"
    stream_interval_seconds: float = 1.0
    price_window_size: int = 60
    sms_dry_run: bool = True
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    risk: RiskThresholds = Field(default_factory=RiskThresholds)

    model_config = SettingsConfigDict(env_prefix="CRYPTO_", env_nested_delimiter="__")


@lru_cache
def get_settings() -> Settings:
    return Settings()
