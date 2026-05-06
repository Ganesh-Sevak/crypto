import logging

import httpx

from .config import Settings
from .models import PriceAlertSubscription

logger = logging.getLogger(__name__)


class SmsClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(
            not self.settings.sms_dry_run
            and self.settings.twilio_account_sid
            and self.settings.twilio_auth_token
            and self.settings.twilio_from_number
        )

    async def send_price_alert(self, subscription: PriceAlertSubscription) -> dict:
        message = (
            f"{subscription.symbol} price alert: ${subscription.last_price:,.2f} is "
            f"{subscription.direction} ${subscription.target_price:,.2f}."
        )
        if not self.enabled:
            logger.info(
                "SMS dry run",
                extra={
                    "phone": self._mask(subscription.phone_number),
                    "symbol": subscription.symbol,
                    "message": message,
                },
            )
            return {"status": "dry_run", "message": message}

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.settings.twilio_account_sid}/Messages.json"
        data = {
            "From": self.settings.twilio_from_number,
            "To": subscription.phone_number,
            "Body": message,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                data=data,
                auth=(self.settings.twilio_account_sid, self.settings.twilio_auth_token),
            )
            response.raise_for_status()
            payload = response.json()
            return {"status": payload.get("status", "sent"), "sid": payload.get("sid")}

    def _mask(self, phone_number: str) -> str:
        return f"{phone_number[:3]}***{phone_number[-2:]}"
