from fastapi.testclient import TestClient

from app.main import app


def test_create_sms_price_alert_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/sms/price-alerts",
            json={
                "phone_number": "+15551234567",
                "symbol": "BTC-USD",
                "direction": "above",
                "target_price": 70000,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sms_mode"] == "dry_run"
    assert body["subscription"]["symbol"] == "BTC-USD"
    assert body["subscription"]["active"] is True


def test_create_sms_price_alert_rejects_unknown_symbol():
    with TestClient(app) as client:
        response = client.post(
            "/sms/price-alerts",
            json={
                "phone_number": "+15551234567",
                "symbol": "DOGE-USD",
                "direction": "above",
                "target_price": 1,
            },
        )

    assert response.status_code == 400


def test_market_data_source_endpoint():
    with TestClient(app) as client:
        response = client.get("/market-data/source")

    assert response.status_code == 200
    body = response.json()
    assert body["stream_source"] in {"simulated", "live"}
    assert body["live_provider"] == "coinbase"
