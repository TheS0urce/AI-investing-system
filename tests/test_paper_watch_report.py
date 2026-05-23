import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_watch_report", SCRIPTS_DIR / "paper_watch_report.py")
paper_watch_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_watch_report)


def test_format_watch_report_includes_status_and_audit_counts():
    summary = {
        "total_ticks": 2,
        "proposal_count": 0,
        "blocked_or_no_proposal_count": 2,
        "auto_submit_enabled": False,
        "watch_statuses": {"EVALUATED": 1, "SKIPPED_MARKET_CLOSED": 1},
        "symbols": {"QQQ": 2},
        "feeds": {"iex": 2},
        "audit_events": {"order_block": 1, "watch_skip": 1},
        "audit_details": {"insufficient_net_edge_after_costs": 1, "market_closed": 1},
    }

    report = paper_watch_report.format_watch_report(summary, "2026-05-23T04:00:00+00:00")

    assert "Total ticks: `2`" in report
    assert "Auto submit enabled: `False`" in report
    assert "- EVALUATED: `1`" in report
    assert "- SKIPPED_MARKET_CLOSED: `1`" in report
    assert "- market_closed: `1`" in report
    assert "does not submit orders" in report
