from datetime import datetime, timezone
from uuid import uuid4

from .models import MetricSnapshot, PriceAlertRequest, PriceAlertSubscription


class PriceAlertStore:
    def __init__(self) -> None:
        self.subscriptions: dict[str, PriceAlertSubscription] = {}

    def add(self, request: PriceAlertRequest) -> PriceAlertSubscription:
        subscription = PriceAlertSubscription(id=str(uuid4()), **request.model_dump())
        self.subscriptions[subscription.id] = subscription
        return subscription

    def list(self) -> list[PriceAlertSubscription]:
        return sorted(self.subscriptions.values(), key=lambda item: item.created_at, reverse=True)

    def evaluate(self, metric: MetricSnapshot) -> list[PriceAlertSubscription]:
        triggered: list[PriceAlertSubscription] = []
        for subscription in self.subscriptions.values():
            if not subscription.active or subscription.symbol != metric.symbol:
                continue
            is_triggered = (
                metric.price >= subscription.target_price
                if subscription.direction == "above"
                else metric.price <= subscription.target_price
            )
            if is_triggered:
                subscription.active = False
                subscription.triggered_at = datetime.now(timezone.utc)
                subscription.last_price = metric.price
                triggered.append(subscription)
        return triggered
