import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_market_session_plan", SCRIPTS_DIR / "paper_market_session_plan.py")
paper_market_session_plan = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_market_session_plan)


def test_session_plan_waits_when_market_closed():
    plan = paper_market_session_plan.session_plan_from_clock(
        {
            "is_open": False,
            "timestamp": "2026-05-23T20:35:22-04:00",
            "next_open": "2026-05-26T09:30:00-04:00",
            "next_close": "2026-05-26T16:00:00-04:00",
        }
    )

    assert plan["status"] == "MARKET-CLOSED-WAIT"
    assert plan["recommended_command"] is None
    assert plan["next_open"] == "2026-05-26T09:30:00-04:00"
    assert plan["operator_timezone"] == "Pacific/Auckland"
    assert plan["next_open_operator"] == "2026-05-27T01:30:00+12:00"


def test_session_plan_recommends_watch_when_market_open():
    plan = paper_market_session_plan.session_plan_from_clock(
        {
            "is_open": True,
            "timestamp": "2026-05-26T10:00:00-04:00",
            "next_open": "2026-05-26T09:30:00-04:00",
            "next_close": "2026-05-26T16:00:00-04:00",
        }
    )

    assert plan["status"] == "MARKET-OPEN-RUN-WATCH"
    assert "run_paper_watch.py" in plan["recommended_command"]
    assert plan["next_close"] == "2026-05-26T16:00:00-04:00"
    assert plan["next_close_operator"] == "2026-05-27T08:00:00+12:00"


def test_session_plan_accepts_operator_timezone():
    plan = paper_market_session_plan.session_plan_from_clock(
        {
            "is_open": False,
            "timestamp": "2026-05-23T20:35:22-04:00",
            "next_open": "2026-05-26T09:30:00-04:00",
            "next_close": "2026-05-26T16:00:00-04:00",
        },
        timezone_name="UTC",
    )

    assert plan["operator_timezone"] == "UTC"
    assert plan["next_open_operator"] == "2026-05-26T13:30:00+00:00"
