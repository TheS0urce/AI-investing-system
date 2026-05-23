import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_ops_evidence", SCRIPTS_DIR / "paper_ops_evidence.py")
paper_ops_evidence = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_ops_evidence)


def test_format_ops_evidence_keeps_safety_state_explicit():
    snapshot = {
        "status": "PAPER-OPS-READY",
        "broker": {"status": "ALPACA-PAPER-READY", "mode": "paper", "live_enabled": False},
        "policy": {
            "autonomous_execution": False,
            "manual_approval_required": True,
            "kill_switch": False,
        },
        "account": {
            "status": "ACTIVE",
            "currency": "USD",
            "cash": "100000",
            "buying_power": "200000",
            "portfolio_value": "100000",
            "pattern_day_trader": False,
            "account_number_masked": "********MARJ",
        },
        "open_orders": [],
        "readiness": {
            "status": "PAPER-GO",
            "checks": [{"name": "live_routing_disabled", "status": "PASS"}],
            "watch_summary": {"total_ticks": 1, "proposal_count": 0},
        },
        "dry_run_drill": {"status": "PAPER-DRILL-READY-NO-SUBMIT", "submit_attempted": False},
        "paper_submission_attempted": False,
        "live_trading_approved": False,
    }

    report = paper_ops_evidence.format_ops_evidence(snapshot, "2026-05-23T03:20:00+00:00")

    assert "Snapshot status: `PAPER-OPS-READY`" in report
    assert "Live routing enabled: `False`" in report
    assert "Dry-run submit attempted: `False`" in report
    assert "Live trading approved: `False`" in report
    assert "This evidence does not approve live trading." in report
