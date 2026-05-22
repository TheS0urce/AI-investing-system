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


def test_market_snapshot_endpoint_uses_read_only_market_data(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    app.config.broker.market_data_base_url = "https://data.alpaca.markets"
    app.config.broker.market_data_feed = "iex"

    called = {}

    def fake_fetch(credentials, symbol, default_volatility_30d):
        called["base_url"] = credentials.base_url
        called["feed"] = credentials.feed
        called["symbol"] = symbol
        return app.MarketSnapshot(
            symbol=symbol,
            price=430.12,
            spread_bps=2.3,
            volume_24h=10_000_000,
            volatility_30d=default_volatility_30d,
            timestamp=app.datetime(2026, 5, 22, tzinfo=app.timezone.utc),
        )

    monkeypatch.setattr(app, "fetch_stock_snapshot", fake_fetch)
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_MARKET_DATA_BASE_URL", "https://data.alpaca.markets")

    response = client(monkeypatch).get(
        "/broker/paper/market_snapshot",
        headers={"X-API-Key": "test-key"},
        params={"symbol": "QQQ", "feed": "iex"},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "alpaca_market_data"
    assert response.json()["snapshot"]["price"] == 430.12
    assert called == {"base_url": "https://data.alpaca.markets", "feed": "iex", "symbol": "QQQ"}


def test_strategy_preview_does_not_auto_submit(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    def fake_fetch(credentials, symbol, default_volatility_30d):
        return app.MarketSnapshot(
            symbol=symbol,
            price=430.12,
            spread_bps=2.3,
            volume_24h=10_000_000,
            volatility_30d=0.01,
            timestamp=app.datetime(2026, 5, 22, tzinfo=app.timezone.utc),
        )

    monkeypatch.setattr(app, "fetch_stock_snapshot", fake_fetch)

    response = client(monkeypatch).get(
        "/broker/paper/strategy_preview",
        headers={"X-API-Key": "test-key"},
        params={"symbol": "QQQ", "cash": 100, "equity": 100, "peak_equity": 100},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "paper_preview_only"
    assert payload["auto_submit_enabled"] is False
    assert payload["manual_confirmation_required"] == "SUBMIT_PAPER_ORDER"
