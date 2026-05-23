import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_daily_ops", SCRIPTS_DIR / "paper_daily_ops.py")
paper_daily_ops = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_daily_ops)


def test_summarize_daily_ops_reports_go_without_live_approval(tmp_path):
    snapshot = {
        "status": "PAPER-OPS-READY",
        "broker": {"status": "ALPACA-PAPER-READY", "mode": "paper", "live_enabled": False},
        "clock": {"is_open": False, "next_open": "2026-05-26T13:30:00Z", "next_close": "2026-05-22T20:00:00Z"},
        "readiness": {"status": "PAPER-GO"},
        "open_orders": [],
        "dry_run_drill": {"status": "PAPER-DRILL-READY-NO-SUBMIT"},
        "paper_submission_attempted": False,
        "live_trading_approved": False,
    }

    summary = paper_daily_ops.summarize_daily_ops(
        snapshot,
        tmp_path / "evidence.md",
        "2026-05-23T03:30:00+00:00",
    )

    assert summary["status"] == "PAPER-DAILY-GO"
    assert summary["broker_mode"] == "paper"
    assert summary["live_enabled"] is False
    assert summary["market_is_open"] is False
    assert summary["next_open"] == "2026-05-26T13:30:00Z"
    assert summary["open_orders"] == 0
    assert summary["paper_submission_attempted"] is False
    assert summary["live_trading_approved"] is False
    assert summary["failed_checks"] == []
    assert summary["reasons"] == []


def test_summarize_daily_ops_reports_no_go_reasons(tmp_path):
    snapshot = {
        "status": "PAPER-OPS-NO-GO",
        "broker": {"status": "ALPACA-PAPER-READY", "mode": "paper", "live_enabled": False},
        "readiness": {
            "status": "PAPER-NO-GO",
            "checks": [
                {"name": "watch_history_has_evidence", "status": "FAIL", "detail": ""},
                {"name": "live_routing_disabled", "status": "PASS", "detail": ""},
            ],
        },
        "open_orders": [{"broker_order_id": "paper-order-1"}],
        "dry_run_drill": {"status": "PAPER-DRILL-NO-GO"},
        "paper_submission_attempted": False,
        "live_trading_approved": False,
    }

    summary = paper_daily_ops.summarize_daily_ops(
        snapshot,
        tmp_path / "evidence.md",
        "2026-05-23T03:30:00+00:00",
    )

    assert summary["status"] == "PAPER-DAILY-NO-GO"
    assert summary["failed_checks"] == [{"name": "watch_history_has_evidence", "status": "FAIL", "detail": ""}]
    assert "snapshot_status=PAPER-OPS-NO-GO" in summary["reasons"]
    assert "watch_history_has_evidence=FAIL" in summary["reasons"]
    assert "open_orders=1" in summary["reasons"]
    assert "dry_run_status=PAPER-DRILL-NO-GO" in summary["reasons"]
