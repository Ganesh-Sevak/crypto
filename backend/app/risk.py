from datetime import datetime, timezone
from uuid import uuid4

from .config import RiskThresholds
from .models import Alert, MetricSnapshot


class RiskEngine:
    def __init__(self, thresholds: RiskThresholds) -> None:
        self.thresholds = thresholds

    def evaluate(self, metric: MetricSnapshot) -> list[Alert]:
        alerts: list[Alert] = []
        if metric.volatility >= self.thresholds.high_volatility:
            alerts.append(self._alert(metric, "HIGH_VOLATILITY", "critical", metric.volatility, self.thresholds.high_volatility))
        if metric.spread >= self.thresholds.wide_spread:
            alerts.append(self._alert(metric, "WIDE_SPREAD", "warning", metric.spread, self.thresholds.wide_spread))
        if metric.liquidity_score <= self.thresholds.low_liquidity:
            alerts.append(self._alert(metric, "LIQUIDITY_DROP", "critical", metric.liquidity_score, self.thresholds.low_liquidity))
        if abs(metric.volume_imbalance) >= self.thresholds.volume_imbalance:
            alerts.append(self._alert(metric, "VOLUME_IMBALANCE", "warning", metric.volume_imbalance, self.thresholds.volume_imbalance))
        return alerts

    def _alert(self, metric: MetricSnapshot, kind: str, severity: str, value: float, threshold: float) -> Alert:
        return Alert(
            id=str(uuid4()),
            symbol=metric.symbol,
            severity=severity,
            type=kind,
            message=f"{metric.symbol} {kind.replace('_', ' ').lower()} detected",
            value=round(value, 6),
            threshold=threshold,
            timestamp=datetime.now(timezone.utc),
        )
