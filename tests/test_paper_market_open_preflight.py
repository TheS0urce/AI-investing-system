import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location(
    "paper_market_open_preflight",
    SCRIPTS_DIR / "paper_market_open_preflight.py",
)
paper_market_open_preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_market_open_preflight)


def test_preflight_reports_go_when_all_gates_pass():
    result = paper_market_open_preflight.summarize_preflight(
        session_plan={
            "status": "MARKET-OPEN-RUN-WATCH",
            "market_is_open": True,
            "next_close": "2026-05-26T16:00:00-04:00",
            "operator_timezone": "Pacific/Auckland",
            "next_close_operator": "2026-05-27T08:00:00+12:00",
            "recommended_command": ".venv/bin/python scripts/run_paper_watch.py",
        },
        readiness={"status": "PAPER-GO", "checks": []},
        strategy_quality={"status": "STRATEGY-QUALITY-OK"},
        open_orders=[],
    )

    assert result["status"] == "PAPER-MARKET-OPEN-GO"
    assert result["reasons"] == []
    assert result["operator_timezone"] == "Pacific/Auckland"
    assert result["next_close_operator"] == "2026-05-27T08:00:00+12:00"
    assert result["auto_submit_enabled"] is False
    assert result["live_trading_approved"] is False


def test_preflight_reports_no_go_reasons():
    result = paper_market_open_preflight.summarize_preflight(
        session_plan={"status": "MARKET-CLOSED-WAIT", "market_is_open": False},
        readiness={
            "status": "PAPER-NO-GO",
            "checks": [
                {"name": "watch_history_has_evidence", "status": "FAIL"},
                {"name": "live_routing_disabled", "status": "PASS"},
            ],
        },
        strategy_quality={"status": "STRATEGY-QUALITY-IMPROVEMENT-REQUIRED"},
        open_orders=[{"broker_order_id": "paper-order-1"}],
    )

    assert result["status"] == "PAPER-MARKET-OPEN-NO-GO"
    assert "session_plan=MARKET-CLOSED-WAIT" in result["reasons"]
    assert "readiness=PAPER-NO-GO" in result["reasons"]
    assert "watch_history_has_evidence=FAIL" in result["reasons"]
    assert "strategy_quality=STRATEGY-QUALITY-IMPROVEMENT-REQUIRED" in result["reasons"]
    assert "open_orders=1" in result["reasons"]
