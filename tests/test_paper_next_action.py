import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_next_action", SCRIPTS_DIR / "paper_next_action.py")
paper_next_action = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_next_action)


def test_next_action_waits_when_market_closed():
    result = paper_next_action.action_from_preflight(
        {
            "status": "PAPER-MARKET-OPEN-NO-GO",
            "reasons": ["session_plan=MARKET-CLOSED-WAIT"],
            "next_open_operator": "2026-05-27T01:30:00+12:00",
            "time_until_next_open": "1d 14h 27m",
        }
    )

    assert result["status"] == "PAPER-NEXT-ACTION-READY"
    assert result["action"] == "WAIT_FOR_MARKET_OPEN"
    assert "2026-05-27T01:30:00+12:00" in result["detail"]
    assert result["auto_submit_enabled"] is False
    assert result["live_trading_approved"] is False


def test_next_action_runs_guarded_watch_when_preflight_go():
    result = paper_next_action.action_from_preflight(
        {
            "status": "PAPER-MARKET-OPEN-GO",
            "reasons": [],
        }
    )

    assert result["action"] == "RUN_GUARDED_WATCH"
    assert "run_market_open_paper_watch.py" in result["command"]


def test_next_action_flags_non_market_reasons():
    result = paper_next_action.action_from_preflight(
        {
            "status": "PAPER-MARKET-OPEN-NO-GO",
            "reasons": ["open_orders=1"],
        }
    )

    assert result["action"] == "FIX_PREFLIGHT_REASONS"
    assert result["reasons"] == ["open_orders=1"]
