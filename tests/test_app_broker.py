from dataclasses import dataclass

from fastapi.testclient import TestClient

import app


@dataclass(frozen=True)
class FakeOrderResult:
    broker_order_id: str = "paper-order-1"
    client_order_id: str | None = "client-1"
    status: str = "accepted"
    symbol: str = "QQQ"
    side: str = "buy"
    submitted_at: str | None = "2026-05-22T00:00:00Z"


def client(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "test-key")
    return TestClient(app.app)


def test_paper_submit_requires_confirmation_phrase(monkeypatch):
    response = client(monkeypatch).post(
        "/broker/paper/submit_order",
        headers={"X-API-Key": "test-key"},
        json={"symbol": "QQQ", "side": "BUY", "quantity": 0.01, "limit_price": 430.0, "confirm": "NO"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "confirmation_phrase_required"


def test_paper_submit_requires_alpaca_ready(monkeypatch):
    app.config.broker.provider = "none"
    app.config.broker.mode = "none"
    app.config.broker.live_enabled = False
    response = client(monkeypatch).post(
        "/broker/paper/submit_order",
        headers={"X-API-Key": "test-key"},
        json={
            "symbol": "QQQ",
            "side": "BUY",
            "quantity": 0.01,
            "limit_price": 430.0,
            "confirm": "SUBMIT_PAPER_ORDER",
        },
    )
    assert response.status_code == 403


def test_paper_submit_uses_paper_adapter_when_confirmed(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    called = {}

    def fake_submit(credentials, order):
        called["base_url"] = credentials.base_url
        called["symbol"] = order.symbol
        return FakeOrderResult()

    monkeypatch.setattr(app, "submit_paper_order", fake_submit)
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    response = client(monkeypatch).post(
        "/broker/paper/submit_order",
        headers={"X-API-Key": "test-key"},
        json={
            "symbol": "QQQ",
            "side": "BUY",
            "quantity": 0.01,
            "limit_price": 430.0,
            "confirm": "SUBMIT_PAPER_ORDER",
        },
    )
    assert response.status_code == 200
    assert response.json()["submitted"] is True
    assert response.json()["broker_order_id"] == "paper-order-1"
    assert called == {"base_url": "https://paper-api.alpaca.markets", "symbol": "QQQ"}


def test_paper_cancel_requires_confirmation_phrase(monkeypatch):
    response = client(monkeypatch).post(
        "/broker/paper/cancel_orders",
        headers={"X-API-Key": "test-key"},
        json={"confirm": "NO"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "confirmation_phrase_required"


def test_paper_cancel_uses_paper_adapter_when_confirmed(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    def fake_cancel(credentials):
        assert credentials.base_url == "https://paper-api.alpaca.markets"
        return [FakeOrderResult()]

    monkeypatch.setattr(app, "cancel_paper_orders", fake_cancel)
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    response = client(monkeypatch).post(
        "/broker/paper/cancel_orders",
        headers={"X-API-Key": "test-key"},
        json={"confirm": "CANCEL_PAPER_ORDERS"},
    )
    assert response.status_code == 200
    assert response.json()["cancel_requested"] is True
    assert response.json()["orders"][0]["broker_order_id"] == "paper-order-1"
