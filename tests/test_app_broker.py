from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import app
from src.ai_investing.preauthorization import (
    LIVE_AUTHORIZATION_CONFIRMATION,
    LIVE_REVOCATION_CONFIRMATION,
    PreauthorizationStore,
)


@dataclass(frozen=True)
class FakeOrderResult:
    broker_order_id: str = "paper-order-1"
    client_order_id: str | None = "client-1"
    status: str = "accepted"
    symbol: str = "QQQ"
    side: str = "buy"
    submitted_at: str | None = "2026-05-22T00:00:00Z"


@dataclass(frozen=True)
class FakePosition:
    symbol: str = "QQQ"
    quantity: float = 0.005
    market_value: float = 2.2
    avg_entry_price: float = 430.0
    current_price: float = 440.0


@dataclass(frozen=True)
class FakeAccountSummary:
    status: str = "ACTIVE"
    currency: str = "USD"
    buying_power: str = "200000"
    cash: str = "100000"
    portfolio_value: str = "100000"
    pattern_day_trader: bool = False
    account_number_masked: str | None = "********1234"


@dataclass(frozen=True)
class FakeClock:
    timestamp: str = "2026-05-22T20:00:00Z"
    is_open: bool = True
    next_open: str = "2026-05-26T13:30:00Z"
    next_close: str = "2026-05-22T20:00:00Z"


def client(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "test-key")
    return TestClient(app.app)


def configure_live(monkeypatch):
    monkeypatch.setattr(app.config.broker, "provider", "alpaca")
    monkeypatch.setattr(app.config.broker, "mode", "live")
    monkeypatch.setattr(app.config.broker, "live_enabled", True)
    monkeypatch.setattr(app.config.broker, "live_base_url", "https://api.alpaca.markets")
    monkeypatch.setattr(app.config.broker, "live_api_key_present", True)
    monkeypatch.setattr(app.config.broker, "live_secret_key_present", True)
    monkeypatch.setattr(app.config.policy, "kill_switch", False)
    monkeypatch.setattr(app.config.risk, "allow_short_sales", False)
    monkeypatch.setenv("ALPACA_LIVE_API_KEY", "live-key")
    monkeypatch.setenv("ALPACA_LIVE_SECRET_KEY", "live-secret")
    monkeypatch.setenv("ALPACA_LIVE_BASE_URL", "https://api.alpaca.markets")


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


def test_paper_submit_rejects_short_sale_for_current_stage(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    response = client(monkeypatch).post(
        "/broker/paper/submit_order",
        headers={"X-API-Key": "test-key"},
        json={
            "symbol": "QQQ",
            "side": "SELL",
            "quantity": 0.002,
            "limit_price": 700.0,
            "confirm": "SUBMIT_PAPER_ORDER",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "short_sale_disabled_for_current_stage"


def test_preauthorization_status_is_inactive_by_default(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "preauthorization_store", PreauthorizationStore(tmp_path / "preauth.json"))

    response = client(monkeypatch).get(
        "/broker/paper/preauthorization",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"
    assert response.json()["paper_only"] is True
    assert response.json()["capital_source"] == "preauthorization_state.current_equity_usd"
    assert response.json()["policy"]["max_order_notional_usd"] == 4.0
    assert response.json()["effective_limits"]["available_capital_usd"] == 100.0
    assert response.json()["effective_limits"]["max_daily_loss_usd"] == 2.0


def test_preauthorization_activation_requires_exact_phrase(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setattr(app, "preauthorization_store", PreauthorizationStore(tmp_path / "preauth.json"))

    response = client(monkeypatch).post(
        "/broker/paper/preauthorization/activate",
        headers={"X-API-Key": "test-key"},
        json={"confirm": "NO"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "preauthorization_confirmation_required"


def test_preauthorized_submit_cannot_reach_broker_while_inactive(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setattr(app, "preauthorization_store", PreauthorizationStore(tmp_path / "preauth.json"))
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock())
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])

    def fail_submit(*args, **kwargs):
        raise AssertionError("inactive authorization reached broker")

    monkeypatch.setattr(app, "submit_paper_order", fail_submit)
    response = client(monkeypatch).post(
        "/broker/paper/preauthorization/submit",
        headers={"X-API-Key": "test-key"},
        json={
            "symbol": "QQQ",
            "side": "BUY",
            "quantity": 0.005,
            "limit_price": 430.0,
            "expected_edge_bps": 12.0,
            "spread_bps": 5.0,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "authorization_inactive_or_expired"


def test_active_preauthorization_submits_bounded_fractional_paper_entry(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    store = PreauthorizationStore(tmp_path / "preauth.json")
    store.activate(confirmation="AUTHORIZE_BOUNDED_PAPER")
    monkeypatch.setattr(app, "preauthorization_store", store)
    monkeypatch.setattr(app, "PROTECTIVE_EXIT_STATE_PATH", tmp_path / "protective_exits.json")
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock())
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])

    called = {}

    def fake_submit(credentials, order):
        called.update(symbol=order.symbol, quantity=order.quantity, limit_price=order.limit_price)
        return FakeOrderResult()

    monkeypatch.setattr(app, "submit_paper_order", fake_submit)
    response = client(monkeypatch).post(
        "/broker/paper/preauthorization/submit",
        headers={"X-API-Key": "test-key"},
        json={
            "symbol": "QQQ",
            "side": "BUY",
            "quantity": 0.005,
            "limit_price": 430.0,
            "expected_edge_bps": 12.0,
            "spread_bps": 5.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["submitted"] is True
    assert response.json()["broker_payload"] == {
        "symbol": "QQQ",
        "qty": "0.005",
        "side": "buy",
        "type": "limit",
        "time_in_force": "day",
        "limit_price": "430.00",
        "extended_hours": False,
    }
    assert response.json()["protection_mode"] == "planned_application_managed_exit_pending_verification"
    assert response.json()["protective_exit"]["stop_price"] == 423.55
    assert response.json()["protective_exit"]["take_profit_price"] == 442.9
    assert called == {"symbol": "QQQ", "quantity": 0.005, "limit_price": 430.0}
    assert store.load().entries_this_session == 1
    exits = app.load_protective_exit_state(tmp_path / "protective_exits.json")
    assert exits["active"][0]["symbol"] == "QQQ"
    assert exits["active"][0]["stop_price"] == 423.55


def test_protective_exit_check_submits_fractional_sell_on_take_profit(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setattr(app, "preauthorization_store", PreauthorizationStore(tmp_path / "preauth.json"))
    monkeypatch.setattr(app, "PROTECTIVE_EXIT_STATE_PATH", tmp_path / "protective_exits.json")
    app.save_protective_exit_state(
        {
            "active": [
                {
                    "symbol": "QQQ",
                    "quantity": 0.005,
                    "entry_price": 430.0,
                    "stop_price": 423.55,
                    "take_profit_price": 442.9,
                    "max_holding_minutes": 360,
                    "entry_broker_order_id": "entry-1",
                    "entry_submitted_at": "2026-05-22T14:00:00Z",
                    "status": "ACTIVE",
                }
            ],
            "history": [],
        },
        tmp_path / "protective_exits.json",
    )
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(timestamp="2026-05-22T15:00:00Z"))
    monkeypatch.setattr(app, "fetch_paper_positions", lambda credentials: [FakePosition(current_price=445.0)])
    monkeypatch.setattr(
        app,
        "fetch_stock_snapshot",
        lambda credentials, symbol: app.MarketSnapshot(
            symbol=symbol,
            price=445.0,
            spread_bps=2.0,
            volume_24h=1_000_000,
            volatility_30d=0.03,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    submitted = {}

    def fake_submit(credentials, order):
        submitted.update(symbol=order.symbol, side=order.side, quantity=order.quantity, limit_price=order.limit_price)
        return FakeOrderResult(symbol=order.symbol, side=order.side.value.lower())

    monkeypatch.setattr(app, "submit_paper_order", fake_submit)

    response = client(monkeypatch).post(
        "/broker/paper/protective_exits/check",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PROTECTIVE-EXIT-SUBMITTED"
    assert response.json()["actions"][0]["reason"] == "take_profit"
    assert submitted == {"symbol": "QQQ", "side": app.Side.SELL, "quantity": 0.005, "limit_price": 445.0}
    exits = app.load_protective_exit_state(tmp_path / "protective_exits.json")
    assert exits["active"] == []
    assert exits["history"][0]["status"] == "EXIT_SUBMITTED"


def test_protective_exit_check_reconciles_filled_sell(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setattr(app, "preauthorization_store", PreauthorizationStore(tmp_path / "preauth.json"))
    monkeypatch.setattr(app, "PROTECTIVE_EXIT_STATE_PATH", tmp_path / "protective_exits.json")
    app.save_protective_exit_state(
        {
            "active": [],
            "history": [
                {
                    "symbol": "QQQ",
                    "quantity": 0.005,
                    "status": "EXIT_SUBMITTED",
                    "exit_broker_order_id": "exit-1",
                }
            ],
        },
        tmp_path / "protective_exits.json",
    )
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setattr(app, "fetch_paper_positions", lambda credentials: [])
    monkeypatch.setattr(
        app,
        "fetch_paper_orders",
        lambda credentials, status, limit: [
            FakeOrderResult(
                broker_order_id="exit-1",
                status="filled",
                symbol="QQQ",
                side="sell",
            )
        ],
    )

    response = client(monkeypatch).post(
        "/broker/paper/protective_exits/check",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PROTECTIVE-EXIT-FILLED"
    assert response.json()["actions"][0]["action"] == "EXIT_FILLED"
    exits = app.load_protective_exit_state(tmp_path / "protective_exits.json")
    assert exits["active"] == []
    assert exits["history"][0]["status"] == "EXIT_FILLED"


def test_protective_exit_check_requeues_rejected_sell(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    store = PreauthorizationStore(tmp_path / "preauth.json")
    store.activate(confirmation="AUTHORIZE_BOUNDED_PAPER")
    monkeypatch.setattr(app, "preauthorization_store", store)
    monkeypatch.setattr(app, "PROTECTIVE_EXIT_STATE_PATH", tmp_path / "protective_exits.json")
    app.save_protective_exit_state(
        {
            "active": [],
            "history": [
                {
                    "symbol": "QQQ",
                    "quantity": 0.005,
                    "entry_price": 430.0,
                    "stop_price": 423.55,
                    "take_profit_price": 442.9,
                    "status": "EXIT_SUBMITTED",
                    "exit_broker_order_id": "exit-1",
                }
            ],
        },
        tmp_path / "protective_exits.json",
    )
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setattr(app, "fetch_paper_positions", lambda credentials: [FakePosition()])
    monkeypatch.setattr(
        app,
        "fetch_paper_orders",
        lambda credentials, status, limit: [
            FakeOrderResult(
                broker_order_id="exit-1",
                status="rejected",
                symbol="QQQ",
                side="sell",
            )
        ],
    )

    response = client(monkeypatch).post(
        "/broker/paper/protective_exits/check",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "MARKET-CLOSED-NO-ACTION"
    assert response.json()["actions"][0]["action"] == "EXIT_REQUEUED"
    exits = app.load_protective_exit_state(tmp_path / "protective_exits.json")
    assert exits["active"][0]["status"] == "ACTIVE"
    assert exits["active"][0]["exit_broker_order_id"] is None
    assert exits["history"][0]["status"] == "EXIT_FAILED"
    assert store.load().active is False
    assert store.load().operational_errors == 1


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


def test_paper_account_endpoint_returns_read_only_safe_fields(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    called = {}

    def fake_fetch_account(credentials):
        called["base_url"] = credentials.base_url
        return FakeAccountSummary()

    monkeypatch.setattr(app, "fetch_paper_account", fake_fetch_account)
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    response = client(monkeypatch).get("/broker/paper/account", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    assert response.json()["mode"] == "read_only"
    assert response.json()["account"]["account_number_masked"] == "********1234"
    assert called == {"base_url": "https://paper-api.alpaca.markets"}


def test_paper_clock_endpoint_returns_read_only_market_clock(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    called = {}

    def fake_fetch_clock(credentials):
        called["base_url"] = credentials.base_url
        return FakeClock()

    monkeypatch.setattr(app, "fetch_paper_clock", fake_fetch_clock)
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    response = client(monkeypatch).get("/broker/paper/clock", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "read_only"
    assert payload["clock"]["is_open"] is True
    assert payload["clock"]["next_open"] == "2026-05-26T13:30:00Z"
    assert called == {"base_url": "https://paper-api.alpaca.markets"}


def test_paper_session_plan_waits_when_market_closed(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    response = client(monkeypatch).get("/broker/paper/session_plan", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "read_only"
    assert payload["status"] == "MARKET-CLOSED-WAIT"
    assert payload["market_is_open"] is False
    assert payload["recommended_command"] is None


def test_paper_session_plan_recommends_watch_when_market_open(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=True))
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    response = client(monkeypatch).get("/broker/paper/session_plan", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "MARKET-OPEN-RUN-WATCH"
    assert payload["market_is_open"] is True
    assert payload["recommended_command"] == (
        ".venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 60 --iterations 30"
    )


def test_strategy_quality_endpoint_is_read_only(monkeypatch):
    response = client(monkeypatch).get("/broker/paper/strategy_quality", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "STRATEGY-QUALITY-OK"
    assert payload["conclusion"] == "current_strategy_can_pass_net_edge_gate"


def test_strategy_scenarios_endpoint_is_synthetic_read_only(monkeypatch):
    response = client(monkeypatch).get("/broker/paper/strategy_scenarios", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-STRATEGY-SCENARIOS-READY"
    assert payload["mode"] == "synthetic_read_only"
    assert payload["auto_submit_enabled"] is False
    assert payload["live_trading_approved"] is False
    scenarios = {item["name"]: item for item in payload["scenarios"]}
    assert scenarios["strong_low_volatility_reaches_manual_review"]["audit_event"] == "manual_review_required"


def test_go_no_go_checklist_endpoint_returns_hard_guards(monkeypatch):
    response = client(monkeypatch).get("/broker/paper/go_no_go_checklist", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-GO-NO-GO-CHECKLIST-READY"
    assert "live_routing_disabled" in payload["hard_guards"]
    assert "operator_approval_required_for_paper_submit" in payload["hard_guards"]
    gates = {item["gate"]: item for item in payload["items"]}
    assert gates["Market session is open"]["go_condition"] == "Status is MARKET-OPEN-RUN-WATCH."


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


def test_strategy_preview_can_use_read_only_paper_account(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True

    def fake_fetch_market(credentials, symbol, default_volatility_30d):
        return app.MarketSnapshot(
            symbol=symbol,
            price=430.12,
            spread_bps=2.3,
            volume_24h=10_000_000,
            volatility_30d=0.01,
            timestamp=app.datetime(2026, 5, 22, tzinfo=app.timezone.utc),
        )

    monkeypatch.setattr(app, "fetch_stock_snapshot", fake_fetch_market)
    monkeypatch.setattr(app, "fetch_paper_account", lambda credentials: FakeAccountSummary())

    response = client(monkeypatch).get(
        "/broker/paper/strategy_preview",
        headers={"X-API-Key": "test-key"},
        params={"symbol": "QQQ", "use_paper_account": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_source"] == "alpaca_paper_account"
    assert payload["account"]["cash"] == "100000"
    assert payload["auto_submit_enabled"] is False


def test_watch_tick_records_preview_without_auto_submit(monkeypatch):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    app.app.state.paper_watch_history = []
    monkeypatch.setattr(app, "append_watch_event", lambda event: None)
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=True))

    def fake_preview(**kwargs):
        return {
            "mode": "paper_preview_only",
            "auto_submit_enabled": False,
            "manual_confirmation_required": "SUBMIT_PAPER_ORDER",
            "market": {
                "symbol": kwargs["symbol"],
                "price": 430.12,
                "spread_bps": 2.3,
                "volume_24h": 10_000_000,
                "volatility_30d": 0.01,
                "timestamp": "2026-05-22T00:00:00+00:00",
            },
            "portfolio_source": "alpaca_paper_account",
            "account": None,
            "order_proposal": None,
            "latest_audit": {"event": "order_block", "severity": "WARN", "details": "test"},
        }

    monkeypatch.setattr(app, "run_paper_strategy_preview", fake_preview)

    response = client(monkeypatch).post(
        "/broker/paper/watch_tick",
        headers={"X-API-Key": "test-key"},
        json={"symbol": "QQQ", "feed": "iex", "use_paper_account": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["auto_submit_enabled"] is False
    assert payload["portfolio_source"] == "alpaca_paper_account"
    assert payload["watch_status"] == "EVALUATED"
    assert payload["clock"]["is_open"] is True
    assert len(app.app.state.paper_watch_history) == 1


def test_watch_tick_skips_strategy_when_market_closed(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    app.app.state.paper_watch_history = []
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=False))

    def fail_preview(**kwargs):
        raise AssertionError("closed market watch tick must not evaluate strategy by default")

    monkeypatch.setattr(app, "run_paper_strategy_preview", fail_preview)

    response = client(monkeypatch).post(
        "/broker/paper/watch_tick",
        headers={"X-API-Key": "test-key"},
        json={"symbol": "QQQ", "feed": "iex", "use_paper_account": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["watch_status"] == "SKIPPED_MARKET_CLOSED"
    assert payload["portfolio_source"] == "not_evaluated"
    assert payload["market"] is None
    assert payload["clock"]["is_open"] is False
    assert payload["latest_audit"]["details"] == "market_closed"


def test_watch_tick_persists_preview_history(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    app.app.state.paper_watch_history = []
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=True))

    def fake_preview(**kwargs):
        return {
            "mode": "paper_preview_only",
            "auto_submit_enabled": False,
            "manual_confirmation_required": "SUBMIT_PAPER_ORDER",
            "market": {
                "symbol": kwargs["symbol"],
                "price": 430.12,
                "spread_bps": 2.3,
                "volume_24h": 10_000_000,
                "volatility_30d": 0.01,
                "timestamp": "2026-05-22T00:00:00+00:00",
            },
            "portfolio_source": "alpaca_paper_account",
            "account": None,
            "order_proposal": None,
            "latest_audit": None,
        }

    monkeypatch.setattr(app, "run_paper_strategy_preview", fake_preview)

    response = client(monkeypatch).post(
        "/broker/paper/watch_tick",
        headers={"X-API-Key": "test-key"},
        json={"symbol": "QQQ", "feed": "iex", "use_paper_account": True},
    )

    assert response.status_code == 200
    assert app.WATCH_HISTORY_PATH.exists()
    assert app.read_watch_events(limit=1)[0]["symbol"] == "QQQ"


def test_watch_history_returns_persisted_recent_events(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event({"symbol": "A"})
    app.append_watch_event({"symbol": "B"})
    app.app.state.paper_watch_history = [{"symbol": "A"}, {"symbol": "B"}]

    response = client(monkeypatch).get(
        "/broker/paper/watch_history",
        headers={"X-API-Key": "test-key"},
        params={"limit": 1},
    )

    assert response.status_code == 200
    assert response.json() == [{"symbol": "B"}]


def test_watch_history_falls_back_to_memory_when_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "missing.jsonl")
    app.app.state.paper_watch_history = [{"symbol": "A"}, {"symbol": "B"}]

    response = client(monkeypatch).get(
        "/broker/paper/watch_history",
        headers={"X-API-Key": "test-key"},
        params={"limit": 1},
    )

    assert response.status_code == 200
    assert response.json() == [{"symbol": "B"}]


def test_watch_history_rejects_invalid_limit(monkeypatch):
    response = client(monkeypatch).get(
        "/broker/paper/watch_history",
        headers={"X-API-Key": "test-key"},
        params={"limit": 0},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "limit_must_be_between_1_and_200"


def test_watch_export_returns_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event(
        {
            "at": "2026-05-22T00:00:00+00:00",
            "symbol": "QQQ",
            "feed": "iex",
            "auto_submit_enabled": False,
            "portfolio_source": "alpaca_paper_account",
            "market": {"price": 430.12, "spread_bps": 2.3},
            "order_proposal": None,
            "latest_audit": {"event": "order_block", "severity": "WARN", "details": "test"},
        }
    )

    response = client(monkeypatch).get(
        "/broker/paper/watch_export",
        headers={"X-API-Key": "test-key"},
        params={"format": "csv", "limit": 10},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "market_price" in response.text
    assert "430.12" in response.text


def test_watch_summary_counts_ticks_and_audit_reasons(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event(
        {
            "symbol": "QQQ",
            "feed": "iex",
            "watch_status": "EVALUATED",
            "auto_submit_enabled": False,
            "order_proposal": None,
            "latest_audit": {"event": "order_block", "details": "insufficient_net_edge_after_costs"},
        }
    )
    app.append_watch_event(
        {
            "symbol": "QQQ",
            "feed": "iex",
            "watch_status": "SKIPPED_MARKET_CLOSED",
            "auto_submit_enabled": False,
            "order_proposal": {"symbol": "QQQ", "side": "BUY"},
            "latest_audit": {"event": "manual_review_required", "details": "proposed BUY"},
        }
    )

    response = client(monkeypatch).get(
        "/broker/paper/watch_summary",
        headers={"X-API-Key": "test-key"},
        params={"limit": 10},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_ticks"] == 2
    assert payload["proposal_count"] == 1
    assert payload["blocked_or_no_proposal_count"] == 1
    assert payload["auto_submit_enabled"] is False
    assert payload["watch_statuses"]["EVALUATED"] == 1
    assert payload["watch_statuses"]["SKIPPED_MARKET_CLOSED"] == 1
    assert payload["audit_details"]["insufficient_net_edge_after_costs"] == 1


def test_watch_summary_rejects_invalid_limit(monkeypatch):
    response = client(monkeypatch).get(
        "/broker/paper/watch_summary",
        headers={"X-API-Key": "test-key"},
        params={"limit": 0},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "limit_must_be_between_1_and_5000"


def test_watch_export_returns_jsonl(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event({"symbol": "QQQ"})

    response = client(monkeypatch).get(
        "/broker/paper/watch_export",
        headers={"X-API-Key": "test-key"},
        params={"format": "jsonl", "limit": 10},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.text == '{"symbol":"QQQ"}\n'


def test_watch_export_rejects_unknown_format(monkeypatch):
    response = client(monkeypatch).get(
        "/broker/paper/watch_export",
        headers={"X-API-Key": "test-key"},
        params={"format": "xlsx"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "format_must_be_csv_or_jsonl"


def test_paper_readiness_returns_go_when_all_paper_checks_pass(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event(
        {
            "symbol": "QQQ",
            "feed": "iex",
            "auto_submit_enabled": False,
            "order_proposal": None,
            "latest_audit": {"event": "order_block", "details": "test"},
        }
    )
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])

    response = client(monkeypatch).get(
        "/broker/paper/readiness",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-GO"
    assert {item["name"]: item["status"] for item in payload["checks"]}["live_routing_disabled"] == "PASS"
    assert payload["watch_summary"]["total_ticks"] == 1


def test_paper_readiness_returns_no_go_without_watch_evidence(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    app.app.state.paper_watch_history = []
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "missing.jsonl")
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])

    response = client(monkeypatch).get(
        "/broker/paper/readiness",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-NO-GO"
    assert {item["name"]: item["status"] for item in payload["checks"]}["watch_history_has_evidence"] == "FAIL"


def test_paper_readiness_rejects_invalid_watch_limit(monkeypatch):
    response = client(monkeypatch).get(
        "/broker/paper/readiness",
        headers={"X-API-Key": "test-key"},
        params={"watch_limit": 0},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "watch_limit_must_be_between_1_and_5000"


def test_market_open_preflight_returns_no_go_when_market_closed(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event({"symbol": "QQQ", "feed": "iex", "auto_submit_enabled": False})

    response = client(monkeypatch).get(
        "/broker/paper/market_open_preflight",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-MARKET-OPEN-NO-GO"
    assert payload["reasons"] == ["session_plan=MARKET-CLOSED-WAIT"]
    assert payload["readiness_status"] == "PAPER-GO"
    assert payload["strategy_quality_status"] == "STRATEGY-QUALITY-OK"
    assert payload["open_orders"] == 0
    assert payload["auto_submit_enabled"] is False
    assert payload["live_trading_approved"] is False


def test_market_open_preflight_returns_go_when_market_open(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=True))
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event({"symbol": "QQQ", "feed": "iex", "auto_submit_enabled": False})

    response = client(monkeypatch).get(
        "/broker/paper/market_open_preflight",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-MARKET-OPEN-GO"
    assert payload["reasons"] == []
    assert payload["recommended_command"] == (
        ".venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 60 --iterations 30"
    )


def test_market_open_preflight_rejects_invalid_watch_limit(monkeypatch):
    response = client(monkeypatch).get(
        "/broker/paper/market_open_preflight",
        headers={"X-API-Key": "test-key"},
        params={"watch_limit": 0},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "watch_limit_must_be_between_1_and_5000"


def test_paper_next_action_waits_when_market_closed(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setenv("ALPACA_PAPER_API_KEY", "paper-key")
    monkeypatch.setenv("ALPACA_PAPER_SECRET_KEY", "paper-secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event({"symbol": "QQQ", "feed": "iex", "auto_submit_enabled": False})

    response = client(monkeypatch).get(
        "/broker/paper/next_action",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-NEXT-ACTION-READY"
    assert payload["action"] == "WAIT_FOR_MARKET_OPEN"
    assert payload["preflight_status"] == "PAPER-MARKET-OPEN-NO-GO"
    assert payload["auto_submit_enabled"] is False
    assert payload["live_trading_approved"] is False


def test_paper_next_action_rejects_invalid_watch_limit(monkeypatch):
    response = client(monkeypatch).get(
        "/broker/paper/next_action",
        headers={"X-API-Key": "test-key"},
        params={"watch_limit": 0},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "watch_limit_must_be_between_1_and_5000"


def test_paper_order_drill_returns_no_submit_payload(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event(
        {
            "symbol": "QQQ",
            "feed": "iex",
            "auto_submit_enabled": False,
            "order_proposal": None,
            "latest_audit": {"event": "order_block", "details": "test"},
        }
    )
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])

    def fail_submit(*args, **kwargs):
        raise AssertionError("paper order drill must not submit")

    monkeypatch.setattr(app, "submit_paper_order", fail_submit)

    response = client(monkeypatch).post(
        "/broker/paper/order_drill",
        headers={"X-API-Key": "test-key"},
        json={"symbol": "QQQ", "side": "BUY", "quantity": 0.001, "limit_price": 1.0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-DRILL-READY-NO-SUBMIT"
    assert payload["readiness_status"] == "PAPER-GO"
    assert payload["submit_attempted"] is False
    assert payload["order_preview"]["submit_enabled"] is False
    assert payload["order_preview"]["payload"]["limit_price"] == "1.00"


def test_paper_order_drill_reports_no_go_without_watch_evidence(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    app.app.state.paper_watch_history = []
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "missing.jsonl")
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])

    response = client(monkeypatch).post(
        "/broker/paper/order_drill",
        headers={"X-API-Key": "test-key"},
        json={},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-DRILL-NO-GO"
    assert payload["readiness_status"] == "PAPER-NO-GO"
    assert payload["submit_attempted"] is False


def test_paper_ops_snapshot_combines_read_only_paper_state(monkeypatch, tmp_path):
    app.config.broker.provider = "alpaca"
    app.config.broker.mode = "paper"
    app.config.broker.live_enabled = False
    app.config.broker.paper_base_url = "https://paper-api.alpaca.markets"
    app.config.broker.paper_api_key_present = True
    app.config.broker.paper_secret_key_present = True
    monkeypatch.setattr(app, "WATCH_HISTORY_PATH", tmp_path / "paper_watch_history.jsonl")
    app.append_watch_event(
        {
            "symbol": "QQQ",
            "feed": "iex",
            "auto_submit_enabled": False,
            "order_proposal": None,
            "latest_audit": {"event": "order_block", "details": "test"},
        }
    )
    monkeypatch.setattr(app, "fetch_paper_account", lambda credentials: FakeAccountSummary())
    monkeypatch.setattr(app, "fetch_paper_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setattr(app, "fetch_paper_orders", lambda credentials, status, limit: [])

    def fail_submit(*args, **kwargs):
        raise AssertionError("paper ops snapshot must not submit")

    monkeypatch.setattr(app, "submit_paper_order", fail_submit)

    response = client(monkeypatch).get(
        "/broker/paper/ops_snapshot",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PAPER-OPS-READY"
    assert payload["broker"]["mode"] == "paper"
    assert payload["broker"]["live_enabled"] is False
    assert payload["policy"]["autonomous_execution"] is False
    assert payload["account"]["status"] == "ACTIVE"
    assert payload["clock"]["is_open"] is False
    assert payload["clock_error"] == ""
    assert payload["open_orders"] == []
    assert payload["readiness"]["status"] == "PAPER-GO"
    assert payload["dry_run_drill"]["submit_attempted"] is False
    assert payload["live_trading_approved"] is False
    assert payload["paper_submission_attempted"] is False


def test_paper_ops_snapshot_rejects_invalid_watch_limit(monkeypatch):
    response = client(monkeypatch).get(
        "/broker/paper/ops_snapshot",
        headers={"X-API-Key": "test-key"},
        params={"watch_limit": 0},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "watch_limit_must_be_between_1_and_5000"


def test_live_readiness_is_disabled_without_master_switch(monkeypatch, tmp_path):
    monkeypatch.setattr(app.config.broker, "provider", "alpaca")
    monkeypatch.setattr(app.config.broker, "mode", "paper")
    monkeypatch.setattr(app.config.broker, "live_enabled", False)
    monkeypatch.setattr(
        app,
        "live_authorization_store",
        PreauthorizationStore(
            tmp_path / "live.json",
            paper_only=False,
            authorization_confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
            revocation_confirmation=LIVE_REVOCATION_CONFIRMATION,
            event_prefix="live",
        ),
    )

    response = client(monkeypatch).get(
        "/broker/live/readiness",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "LIVE-NO-GO"
    assert response.json()["broker"]["status"] == "LIVE-DISABLED"


def test_dashboard_summary_reports_live_readiness_in_live_mode(monkeypatch):
    configure_live(monkeypatch)

    response = client(monkeypatch).get(
        "/dashboard/summary",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["broker"]["status"] == "ALPACA-LIVE-READY"
    assert response.json()["broker"]["ready"] is True


def test_live_readiness_requires_expected_empty_account(monkeypatch, tmp_path):
    configure_live(monkeypatch)
    monkeypatch.setattr(
        app,
        "live_authorization_store",
        PreauthorizationStore(
            tmp_path / "live.json",
            paper_only=False,
            authorization_confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
            revocation_confirmation=LIVE_REVOCATION_CONFIRMATION,
            event_prefix="live",
        ),
    )
    monkeypatch.setattr(
        app,
        "fetch_live_account",
        lambda credentials: FakeAccountSummary(
            buying_power="300",
            cash="300",
            portfolio_value="300",
        ),
    )
    monkeypatch.setattr(app, "fetch_live_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setattr(app, "fetch_live_orders", lambda credentials, status, limit: [])
    monkeypatch.setattr(app, "fetch_live_positions", lambda credentials: [])

    response = client(monkeypatch).get(
        "/broker/live/readiness",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "LIVE-PREFLIGHT-GO"
    assert response.json()["account"]["portfolio_value"] == "300"
    assert all(check["status"] == "PASS" for check in response.json()["checks"])


def test_live_authorization_requires_exact_phrase_and_verified_account(monkeypatch, tmp_path):
    configure_live(monkeypatch)
    store = PreauthorizationStore(
        tmp_path / "live.json",
        paper_only=False,
        authorization_confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        revocation_confirmation=LIVE_REVOCATION_CONFIRMATION,
        event_prefix="live",
    )
    monkeypatch.setattr(app, "live_authorization_store", store)
    monkeypatch.setattr(
        app,
        "fetch_live_account",
        lambda credentials: FakeAccountSummary(
            buying_power="300",
            cash="300",
            portfolio_value="300",
        ),
    )
    monkeypatch.setattr(app, "fetch_live_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setattr(app, "fetch_live_orders", lambda credentials, status, limit: [])
    monkeypatch.setattr(app, "fetch_live_positions", lambda credentials: [])

    rejected = client(monkeypatch).post(
        "/broker/live/authorization/activate",
        headers={"X-API-Key": "test-key"},
        json={"confirm": "AUTHORIZE_BOUNDED_PAPER"},
    )
    accepted = client(monkeypatch).post(
        "/broker/live/authorization/activate",
        headers={"X-API-Key": "test-key"},
        json={"confirm": LIVE_AUTHORIZATION_CONFIRMATION},
    )

    assert rejected.status_code == 400
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACTIVE"
    assert accepted.json()["authorization"]["paper_only"] is False
    assert accepted.json()["authorization"]["current_equity_usd"] == 300.0
    assert accepted.json()["effective_limits"]["max_order_notional_usd"] == 12.0


def test_live_submit_is_blocked_without_live_authorization(monkeypatch, tmp_path):
    configure_live(monkeypatch)
    monkeypatch.setattr(
        app,
        "live_authorization_store",
        PreauthorizationStore(
            tmp_path / "live.json",
            paper_only=False,
            authorization_confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
            revocation_confirmation=LIVE_REVOCATION_CONFIRMATION,
            event_prefix="live",
        ),
    )
    monkeypatch.setattr(
        app,
        "fetch_live_account",
        lambda credentials: FakeAccountSummary(
            buying_power="300",
            cash="300",
            portfolio_value="300",
        ),
    )
    monkeypatch.setattr(app, "fetch_live_clock", lambda credentials: FakeClock())
    monkeypatch.setattr(app, "fetch_live_orders", lambda credentials, status, limit: [])
    monkeypatch.setattr(app, "fetch_live_positions", lambda credentials: [])

    def fail_submit(*args, **kwargs):
        raise AssertionError("inactive live authorization reached broker")

    monkeypatch.setattr(app, "submit_live_order", fail_submit)
    response = client(monkeypatch).post(
        "/broker/live/authorization/submit",
        headers={"X-API-Key": "test-key"},
        json={
            "symbol": "QQQ",
            "side": "BUY",
            "quantity": 0.008,
            "limit_price": 700.0,
            "expected_edge_bps": 10.0,
            "spread_bps": 5.0,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "authorization_inactive_or_expired"


def test_active_live_authorization_submits_bounded_order_and_records_protection(monkeypatch, tmp_path):
    configure_live(monkeypatch)
    store = PreauthorizationStore(
        tmp_path / "live.json",
        paper_only=False,
        authorization_confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        revocation_confirmation=LIVE_REVOCATION_CONFIRMATION,
        event_prefix="live",
    )
    store.activate(
        confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        policy=app.live_authorization_policy,
        available_capital_usd=300.0,
    )
    monkeypatch.setattr(app, "live_authorization_store", store)
    monkeypatch.setattr(app, "LIVE_PROTECTIVE_EXIT_STATE_PATH", tmp_path / "live_exits.json")
    monkeypatch.setattr(
        app,
        "fetch_live_account",
        lambda credentials: FakeAccountSummary(
            buying_power="300",
            cash="300",
            portfolio_value="300",
        ),
    )
    monkeypatch.setattr(app, "fetch_live_clock", lambda credentials: FakeClock())
    monkeypatch.setattr(app, "fetch_live_orders", lambda credentials, status, limit: [])
    monkeypatch.setattr(app, "fetch_live_positions", lambda credentials: [])
    monkeypatch.setattr(
        app,
        "submit_live_order",
        lambda credentials, order: FakeOrderResult(
            broker_order_id="live-order-1",
            symbol=order.symbol,
            side=order.side.value.lower(),
        ),
    )

    response = client(monkeypatch).post(
        "/broker/live/authorization/submit",
        headers={"X-API-Key": "test-key"},
        json={
            "symbol": "QQQ",
            "side": "BUY",
            "quantity": 0.008,
            "limit_price": 700.0,
            "expected_edge_bps": 10.0,
            "spread_bps": 5.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["submitted"] is True
    assert response.json()["real_money"] is True
    assert response.json()["authorization_reason"] == "preauthorized_live_entry"
    assert response.json()["broker_order"]["broker_order_id"] == "live-order-1"
    exits = app.load_protective_exit_state(tmp_path / "live_exits.json")
    assert exits["active"][0]["entry_broker_order_id"] == "live-order-1"
    assert exits["active"][0]["status"] == "ACTIVE"


def test_live_emergency_stop_revokes_and_cancels_orders(monkeypatch, tmp_path):
    configure_live(monkeypatch)
    store = PreauthorizationStore(
        tmp_path / "live.json",
        paper_only=False,
        authorization_confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        revocation_confirmation=LIVE_REVOCATION_CONFIRMATION,
        event_prefix="live",
    )
    store.activate(
        confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        policy=app.live_authorization_policy,
        available_capital_usd=300.0,
    )
    monkeypatch.setattr(app, "live_authorization_store", store)
    monkeypatch.setattr(
        app,
        "cancel_live_orders",
        lambda credentials: [
            FakeOrderResult(
                broker_order_id="live-order-1",
                status="canceled",
                symbol="QQQ",
                side="buy",
            )
        ],
    )

    response = client(monkeypatch).post(
        "/broker/live/emergency_stop",
        headers={"X-API-Key": "test-key"},
        json={"confirm": "STOP_LIVE_TRADING"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "LIVE-STOPPED"
    assert response.json()["authorization_active"] is False
    assert response.json()["canceled_orders"][0]["status"] == "canceled"
    assert store.load().active is False


def test_live_protection_archives_canceled_entry_and_pauses_new_entries(monkeypatch, tmp_path):
    configure_live(monkeypatch)
    store = PreauthorizationStore(
        tmp_path / "live.json",
        paper_only=False,
        authorization_confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        revocation_confirmation=LIVE_REVOCATION_CONFIRMATION,
        event_prefix="live",
    )
    store.activate(
        confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        policy=app.live_authorization_policy,
        available_capital_usd=300.0,
    )
    monkeypatch.setattr(app, "live_authorization_store", store)
    monkeypatch.setattr(app, "LIVE_PROTECTIVE_EXIT_STATE_PATH", tmp_path / "live_exits.json")
    app.save_protective_exit_state(
        {
            "active": [
                {
                    "symbol": "QQQ",
                    "quantity": 0.008,
                    "entry_price": 700.0,
                    "stop_price": 689.5,
                    "take_profit_price": 721.0,
                    "max_holding_minutes": 360,
                    "entry_broker_order_id": "live-entry-1",
                    "entry_submitted_at": "2026-06-30T14:00:00Z",
                    "status": "ACTIVE",
                }
            ],
            "history": [],
        },
        tmp_path / "live_exits.json",
    )
    monkeypatch.setattr(app, "fetch_live_clock", lambda credentials: FakeClock())
    monkeypatch.setattr(app, "fetch_live_positions", lambda credentials: [])
    monkeypatch.setattr(
        app,
        "fetch_live_orders",
        lambda credentials, status, limit: [
            FakeOrderResult(
                broker_order_id="live-entry-1",
                status="canceled",
                symbol="QQQ",
                side="buy",
            )
        ],
    )

    response = client(monkeypatch).post(
        "/broker/live/protective_exits/check",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["actions"][0]["action"] == "ENTRY_FAILED"
    exits = app.load_protective_exit_state(tmp_path / "live_exits.json")
    assert exits["active"] == []
    assert exits["history"][0]["status"] == "ENTRY_FAILED"
    assert store.load().active is False
    assert store.load().operational_errors == 1


def test_live_protection_records_filled_exit_performance(monkeypatch, tmp_path):
    configure_live(monkeypatch)
    store = PreauthorizationStore(
        tmp_path / "live.json",
        paper_only=False,
        authorization_confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        revocation_confirmation=LIVE_REVOCATION_CONFIRMATION,
        event_prefix="live",
    )
    store.activate(
        confirmation=LIVE_AUTHORIZATION_CONFIRMATION,
        policy=app.live_authorization_policy,
        available_capital_usd=300.0,
    )
    store.record_entry(
        session_date="2026-06-30",
        order_notional_usd=10.0,
        symbol="QQQ",
    )
    monkeypatch.setattr(app, "live_authorization_store", store)
    monkeypatch.setattr(app, "LIVE_PROTECTIVE_EXIT_STATE_PATH", tmp_path / "live_exits.json")
    app.save_protective_exit_state(
        {
            "active": [],
            "history": [
                {
                    "symbol": "QQQ",
                    "quantity": 0.1,
                    "entry_price": 100.0,
                    "status": "EXIT_SUBMITTED",
                    "exit_broker_order_id": "live-exit-1",
                    "exit_limit_price": 103.0,
                }
            ],
        },
        tmp_path / "live_exits.json",
    )
    monkeypatch.setattr(app, "fetch_live_clock", lambda credentials: FakeClock(is_open=False))
    monkeypatch.setattr(app, "fetch_live_positions", lambda credentials: [])
    monkeypatch.setattr(
        app,
        "fetch_live_orders",
        lambda credentials, status, limit: [
            FakeOrderResult(
                broker_order_id="live-exit-1",
                status="filled",
                symbol="QQQ",
                side="sell",
            )
        ],
    )
    monkeypatch.setattr(
        app,
        "fetch_live_account",
        lambda credentials: FakeAccountSummary(
            buying_power="300.30",
            cash="300.30",
            portfolio_value="300.30",
        ),
    )

    response = client(monkeypatch).post(
        "/broker/live/protective_exits/check",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PROTECTIVE-EXIT-FILLED"
    assert response.json()["actions"][0]["realized_pnl_usd"] == 0.3
    state = store.load()
    assert state.closed_trades == 1
    assert state.winning_trades == 1
    assert state.realized_pnl_usd == 0.3
    assert state.current_equity_usd == 300.3
    assert state.gross_exposure_usd == 0.0
