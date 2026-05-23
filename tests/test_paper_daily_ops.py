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
    assert summary["open_orders"] == 0
    assert summary["paper_submission_attempted"] is False
    assert summary["live_trading_approved"] is False
