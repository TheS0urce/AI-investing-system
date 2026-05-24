import importlib.util
import sys
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
        session_plan={"status": "MARKET-CLOSED-WAIT", "market_is_open": False},
        post_tick=lambda *args: called.append(args) or {},
    )

    assert result == 1
    assert called == []
    assert "PAPER-WATCH-NO-GO" in capsys.readouterr().out


def test_guarded_watch_runs_read_only_ticks_when_market_open(capsys):
    calls = []

    def fake_post_tick(api_base, api_key, symbol, feed, allow_closed_market):
        calls.append(
            {
                "api_base": api_base,
                "api_key": api_key,
                "symbol": symbol,
                "feed": feed,
                "allow_closed_market": allow_closed_market,
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
        session_plan={"status": "MARKET-OPEN-RUN-WATCH", "market_is_open": True},
        post_tick=fake_post_tick,
        sleep=lambda seconds: None,
    )

    assert result == 0
    assert len(calls) == 2
    assert all(call["allow_closed_market"] is False for call in calls)
    output = capsys.readouterr().out
    assert "PAPER-WATCH-RUNNING" in output
    assert output.count("WATCH-TICK-OK") == 2
