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
