import json

import pytest

from src.ai_investing import alpaca_live
from src.ai_investing.alpaca_live import (
    AlpacaLiveCredentials,
    ensure_live_credentials,
    fetch_live_account,
    submit_live_order,
)
from src.ai_investing.models import OrderProposal, Side


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_live_credentials_reject_paper_domain():
    with pytest.raises(RuntimeError, match="alpaca_live_domain_guard_failed"):
        ensure_live_credentials(
            AlpacaLiveCredentials(
                "key",
                "secret",
                "https://paper-api.alpaca.markets",
            )
        )


def test_fetch_live_account_uses_production_domain_and_live_headers(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout, context):
        captured["url"] = request.full_url
        captured["key"] = request.headers["Apca-api-key-id"]
        return FakeResponse(
            {
                "status": "ACTIVE",
                "currency": "USD",
                "buying_power": "300",
                "cash": "300",
                "portfolio_value": "300",
                "pattern_day_trader": False,
                "account_number": "LIVE1234",
            }
        )

    monkeypatch.setattr(alpaca_live, "urlopen", fake_urlopen)
    account = fetch_live_account(AlpacaLiveCredentials("live-key", "live-secret"))

    assert captured == {
        "url": "https://api.alpaca.markets/v2/account",
        "key": "live-key",
    }
    assert account.portfolio_value == "300"
    assert account.account_number_masked == "****1234"


def test_submit_live_order_is_fractional_limit_day_without_extended_hours(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout, context):
        captured["url"] = request.full_url
        captured["method"] = request.method
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "id": "live-order-1",
                "client_order_id": "client-1",
                "status": "accepted",
                "symbol": "QQQ",
                "side": "buy",
                "submitted_at": "2026-06-30T14:00:00Z",
            }
        )

    monkeypatch.setattr(alpaca_live, "urlopen", fake_urlopen)
    result = submit_live_order(
        AlpacaLiveCredentials("live-key", "live-secret"),
        OrderProposal("QQQ", Side.BUY, 0.008, 700.0, 10.0, "test"),
    )

    assert captured["url"] == "https://api.alpaca.markets/v2/orders"
    assert captured["method"] == "POST"
    assert captured["payload"] == {
        "symbol": "QQQ",
        "qty": "0.008",
        "side": "buy",
        "type": "limit",
        "time_in_force": "day",
        "limit_price": "700.00",
        "extended_hours": False,
    }
    assert result.broker_order_id == "live-order-1"
