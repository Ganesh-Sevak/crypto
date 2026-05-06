from datetime import datetime, timezone

from app.config import RiskThresholds
from app.models import MetricSnapshot
from app.risk import RiskEngine


def metric(**overrides) -> MetricSnapshot:
    defaults = {
        "symbol": "ETH-USD",
        "price": 3000.0,
        "volatility": 0.005,
        "spread": 0.001,
        "spread_bps": 10.0,
        "vwap": 2998.0,
        "rolling_price_change": 0.002,
        "liquidity_score": 75.0,
        "volume_imbalance": 0.1,
        "timestamp": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return MetricSnapshot(**defaults)


def test_risk_engine_returns_no_alerts_for_normal_metrics():
    engine = RiskEngine(RiskThresholds())

    assert engine.evaluate(metric()) == []


def test_risk_engine_flags_all_threshold_breaches():
    engine = RiskEngine(RiskThresholds(high_volatility=0.01, wide_spread=0.003, low_liquidity=40.0, volume_imbalance=0.5))

    alerts = engine.evaluate(metric(volatility=0.02, spread=0.006, liquidity_score=20.0, volume_imbalance=-0.7))
    alert_types = {alert.type for alert in alerts}

    assert alert_types == {"HIGH_VOLATILITY", "WIDE_SPREAD", "LIQUIDITY_DROP", "VOLUME_IMBALANCE"}
    assert {alert.symbol for alert in alerts} == {"ETH-USD"}
