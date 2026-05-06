from datetime import datetime, timezone

from app.metrics import calculate_metrics, sample_volatility
from app.models import MarketTick


def tick(price: float = 100.0, bid: float = 99.9, ask: float = 100.1) -> MarketTick:
    return MarketTick(
        symbol="BTC-USD",
        price=price,
        bid=bid,
        ask=ask,
        bid_size=120.0,
        ask_size=80.0,
        volume=10.0,
        timestamp=datetime.now(timezone.utc),
    )


def test_calculate_metrics_outputs_expected_spread_vwap_and_imbalance():
    metric = calculate_metrics(
        tick(),
        prices=[98.0, 100.0],
        volumes=[20.0, 10.0],
        bid_sizes=[110.0, 120.0],
        ask_sizes=[90.0, 80.0],
    )

    assert metric.spread == 0.002
    assert metric.spread_bps == 20.0
    assert metric.vwap == 98.67
    assert metric.rolling_price_change == 0.020408
    assert metric.volume_imbalance == 0.2
    assert metric.liquidity_score > 0


def test_sample_volatility_handles_short_series():
    assert sample_volatility([]) == 0.0
    assert sample_volatility([100.0]) == 0.0


def test_sample_volatility_returns_positive_for_moving_prices():
    assert sample_volatility([100.0, 101.0, 99.0, 103.0]) > 0
