import importlib.util
import io
import sys
import urllib.error
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location(
    "run_market_open_paper_watch",
    SCRIPTS_DIR / "run_market_open_paper_watch.py",
)
run_market_open_paper_watch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_market_open_paper_watch)


def test_guarded_watch_refuses_when_market_closed(capsys):
    called = []

    result = run_market_open_paper_watch.run_guarded_watch(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        symbol="QQQ",
        feed="iex",
        interval_seconds=60,
        iterations=1,
        preflight={
            "status": "PAPER-MARKET-OPEN-NO-GO",
            "reasons": ["session_plan=MARKET-CLOSED-WAIT"],
            "market_is_open": False,
        },
        post_tick=lambda *args: called.append(args) or {},
    )

    assert result == 1
    assert called == []
    output = capsys.readouterr().out
    assert "PAPER-WATCH-NO-GO" in output
    assert "market_open_preflight_failed" in output


def test_wait_for_market_open_preflight_retries_closed_then_open(capsys):
    calls = []
    preflights = [
        {
            "status": "PAPER-MARKET-OPEN-NO-GO",
            "reasons": ["session_plan=MARKET-CLOSED-WAIT"],
            "market_is_open": False,
        },
        {
            "status": "PAPER-MARKET-OPEN-NO-GO",
            "reasons": ["session_plan=MARKET-CLOSED-WAIT"],
            "market_is_open": False,
        },
        {"status": "PAPER-MARKET-OPEN-GO", "market_is_open": True},
    ]

    result = run_market_open_paper_watch.wait_for_market_open_preflight(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        attempts=3,
        retry_delay_seconds=300,
        fetch_preflight=lambda api_base, api_key: preflights[len(calls)],
        sleep=lambda seconds: calls.append(seconds),
    )

    assert result["status"] == "PAPER-MARKET-OPEN-GO"
    assert calls == [300, 300]
    assert capsys.readouterr().out.count("PREFLIGHT-CHECK") == 3


def test_wait_for_market_open_preflight_stops_after_attempts_when_still_closed():
    sleeps = []

    result = run_market_open_paper_watch.wait_for_market_open_preflight(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        attempts=3,
        retry_delay_seconds=300,
        fetch_preflight=lambda api_base, api_key: {
            "status": "PAPER-MARKET-OPEN-NO-GO",
            "reasons": ["session_plan=MARKET-CLOSED-WAIT"],
            "market_is_open": False,
        },
        sleep=lambda seconds: sleeps.append(seconds),
    )

    assert result["status"] == "PAPER-MARKET-OPEN-NO-GO"
    assert sleeps == [300, 300]


def test_wait_for_market_open_preflight_does_not_retry_non_session_failure():
    sleeps = []

    result = run_market_open_paper_watch.wait_for_market_open_preflight(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        attempts=3,
        retry_delay_seconds=300,
        fetch_preflight=lambda api_base, api_key: {
            "status": "PAPER-MARKET-OPEN-NO-GO",
            "reasons": ["open_orders=1"],
            "market_is_open": True,
        },
        sleep=lambda seconds: sleeps.append(seconds),
    )

    assert result["status"] == "PAPER-MARKET-OPEN-NO-GO"
    assert sleeps == []


def test_guarded_watch_refuses_when_preflight_has_non_session_reason(capsys):
    called = []

    result = run_market_open_paper_watch.run_guarded_watch(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        symbol="QQQ",
        feed="iex",
        interval_seconds=60,
        iterations=1,
        preflight={
            "status": "PAPER-MARKET-OPEN-NO-GO",
            "reasons": ["open_orders=1"],
            "market_is_open": True,
        },
        post_tick=lambda *args: called.append(args) or {},
    )

    assert result == 1
    assert called == []
    output = capsys.readouterr().out
    assert "open_orders=1" in output


def test_guarded_watch_runs_read_only_ticks_when_market_open(capsys):
    calls = []

    def fake_post_tick(
        api_base,
        api_key,
        symbol,
        feed,
        allow_closed_market,
        use_paper_account=True,
        cash=1_000.0,
        equity=1_000.0,
        peak_equity=1_000.0,
        daily_pnl=0.0,
        consecutive_losses=0,
    ):
        calls.append(
            {
                "api_base": api_base,
                "api_key": api_key,
                "symbol": symbol,
                "feed": feed,
                "allow_closed_market": allow_closed_market,
                "use_paper_account": use_paper_account,
                "cash": cash,
                "equity": equity,
                "peak_equity": peak_equity,
                "daily_pnl": daily_pnl,
                "consecutive_losses": consecutive_losses,
            }
        )
        return {"watch_status": "EVALUATED", "order_proposal": None}

    result = run_market_open_paper_watch.run_guarded_watch(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        symbol="QQQ",
        feed="iex",
        interval_seconds=60,
        iterations=2,
        preflight={"status": "PAPER-MARKET-OPEN-GO", "market_is_open": True},
        post_tick=fake_post_tick,
        sleep=lambda seconds: None,
    )

    assert result == 0
    assert len(calls) == 2
    assert all(call["allow_closed_market"] is False for call in calls)
    assert all(call["use_paper_account"] is True for call in calls)
    output = capsys.readouterr().out
    assert "PAPER-WATCH-RUNNING" in output
    assert "PAPER-MARKET-OPEN-GO" in output
    assert output.count("WATCH-TICK-OK") == 2


def test_guarded_watch_passes_simulated_capital_to_ticks(capsys):
    calls = []

    def fake_post_tick(*args):
        calls.append(args)
        return {"watch_status": "EVALUATED", "order_proposal": None}

    result = run_market_open_paper_watch.run_guarded_watch(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        symbol="AAPL",
        feed="iex",
        interval_seconds=60,
        iterations=1,
        preflight={"status": "PAPER-MARKET-OPEN-GO", "market_is_open": True},
        use_paper_account=False,
        cash=100.0,
        equity=100.0,
        peak_equity=100.0,
        daily_pnl=0.0,
        consecutive_losses=0,
        post_tick=fake_post_tick,
    )

    assert result == 0
    assert calls == [
        (
            "http://127.0.0.1:8001",
            "test-key",
            "AAPL",
            "iex",
            False,
            False,
            100.0,
            100.0,
            100.0,
            0.0,
            0,
        )
    ]
    output = capsys.readouterr().out
    assert '"use_paper_account": false' in output
    assert '"simulated_equity": 100.0' in output


def test_guarded_watch_can_submit_preauthorized_proposal(capsys):
    submits = []

    def fake_post_tick(*args):
        return {
            "watch_status": "EVALUATED",
            "market": {"spread_bps": 1.5},
            "order_proposal": {
                "symbol": "QQQ",
                "side": "buy",
                "quantity": 0.002,
                "limit_price": 500.0,
                "expected_edge_bps": 12.0,
                "reason": "test",
            },
        }

    def fake_submit(api_base, api_key, event):
        submits.append((api_base, api_key, event["order_proposal"]["symbol"]))
        return {"submitted": True, "broker_order": {"symbol": "QQQ"}}

    result = run_market_open_paper_watch.run_guarded_watch(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        symbol="QQQ",
        feed="iex",
        interval_seconds=60,
        iterations=1,
        preflight={"status": "PAPER-MARKET-OPEN-GO", "market_is_open": True},
        post_tick=fake_post_tick,
        submit_preauthorized=fake_submit,
        enable_preauthorized_submit=True,
    )

    assert result == 0
    assert submits == [("http://127.0.0.1:8001", "test-key", "QQQ")]
    output = capsys.readouterr().out
    assert "PREAUTHORIZED-SUBMIT-OK" in output


def test_guarded_watch_stops_preauthorized_submits_after_block(capsys):
    submit_calls = 0

    def fake_post_tick(*args):
        return {
            "watch_status": "EVALUATED",
            "market": {"spread_bps": 1.5},
            "order_proposal": {
                "symbol": "QQQ",
                "side": "buy",
                "quantity": 0.002,
                "limit_price": 500.0,
                "expected_edge_bps": 12.0,
                "reason": "test",
            },
        }

    def fake_submit(*args):
        nonlocal submit_calls
        submit_calls += 1
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:8001/broker/paper/preauthorization/submit",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=io.BytesIO(b'{"detail":{"reason":"authorization_inactive_or_expired"}}'),
        )

    result = run_market_open_paper_watch.run_guarded_watch(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        symbol="QQQ",
        feed="iex",
        interval_seconds=60,
        iterations=2,
        preflight={"status": "PAPER-MARKET-OPEN-GO", "market_is_open": True},
        post_tick=fake_post_tick,
        submit_preauthorized=fake_submit,
        enable_preauthorized_submit=True,
        sleep=lambda seconds: None,
    )

    assert result == 0
    assert submit_calls == 1
    output = capsys.readouterr().out
    assert "PREAUTHORIZED-SUBMIT-BLOCKED" in output
    assert "authorization_inactive_or_expired" in output


def test_parse_symbols_deduplicates_and_normalizes():
    symbols = run_market_open_paper_watch.parse_symbols("spy, QQQ,spy,BRK.B", "QQQ")

    assert symbols == ["SPY", "QQQ", "BRK.B"]


def test_parse_symbols_rejects_empty_list():
    try:
        run_market_open_paper_watch.parse_symbols(" , ", "QQQ")
    except ValueError as exc:
        assert str(exc) == "symbols_required"
    else:
        raise AssertionError("expected symbols_required")


def test_guarded_watchlist_runs_read_only_ticks_for_each_symbol_and_cycle(capsys):
    calls = []

    def fake_post_tick(api_base, api_key, symbol, feed, allow_closed_market, use_paper_account=True, *args):
        calls.append((symbol, allow_closed_market, use_paper_account))
        return {"watch_status": "EVALUATED", "order_proposal": None}

    result = run_market_open_paper_watch.run_guarded_watchlist(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        symbols=["SPY", "QQQ"],
        feed="iex",
        interval_seconds=60,
        iterations=2,
        preflight={"status": "PAPER-MARKET-OPEN-GO"},
        post_tick=fake_post_tick,
        sleep=lambda seconds: None,
    )

    assert result == 0
    assert calls == [("SPY", False, True), ("QQQ", False, True), ("SPY", False, True), ("QQQ", False, True)]
    output = capsys.readouterr().out
    assert "PAPER-WATCHLIST-RUNNING" in output
    assert output.count("WATCHLIST-TICK-OK") == 4


def test_guarded_watchlist_refuses_when_preflight_fails(capsys):
    calls = []

    result = run_market_open_paper_watch.run_guarded_watchlist(
        api_base="http://127.0.0.1:8001",
        api_key="test-key",
        symbols=["SPY", "QQQ"],
        feed="iex",
        interval_seconds=60,
        iterations=1,
        preflight={"status": "PAPER-MARKET-OPEN-NO-GO", "reasons": ["open_orders=1"]},
        post_tick=lambda *args: calls.append(args) or {},
    )

    assert result == 1
    assert calls == []
    assert "PAPER-WATCHLIST-NO-GO" in capsys.readouterr().out
