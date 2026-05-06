from datetime import datetime, timezone

from app.models import MetricSnapshot, PriceAlertRequest
from app.price_alerts import PriceAlertStore


def metric(price: float, symbol: str = "BTC-USD") -> MetricSnapshot:
    return MetricSnapshot(
        symbol=symbol,
        price=price,
        volatility=0.01,
        spread=0.001,
        spread_bps=10.0,
        vwap=price,
        rolling_price_change=0.0,
        liquidity_score=80.0,
        volume_imbalance=0.0,
        timestamp=datetime.now(timezone.utc),
    )


def test_price_alert_triggers_once_when_price_moves_above_target():
    store = PriceAlertStore()
    subscription = store.add(
        PriceAlertRequest(phone_number="+15551234567", symbol="BTC-USD", direction="above", target_price=105.0)
    )

    assert store.evaluate(metric(104.0)) == []
    triggered = store.evaluate(metric(105.01))

    assert [item.id for item in triggered] == [subscription.id]
    assert triggered[0].active is False
    assert triggered[0].last_price == 105.01
    assert store.evaluate(metric(110.0)) == []


def test_price_alert_triggers_when_price_moves_below_target():
    store = PriceAlertStore()
    store.add(PriceAlertRequest(phone_number="+15551234567", symbol="ETH-USD", direction="below", target_price=90.0))

    assert store.evaluate(metric(91.0, symbol="ETH-USD")) == []
    assert len(store.evaluate(metric(89.5, symbol="ETH-USD"))) == 1
