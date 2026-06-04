import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location(
    "paper_proposal_blocker_report",
    SCRIPTS_DIR / "paper_proposal_blocker_report.py",
)
paper_proposal_blocker_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["paper_proposal_blocker_report"] = paper_proposal_blocker_report
SPEC.loader.exec_module(paper_proposal_blocker_report)


def test_proposal_blocker_report_identifies_edge_shortfall_after_liquidity_pass():
    events = [
        {
            "at": "2026-06-03T13:30:40+00:00",
            "watch_status": "EVALUATED",
            "order_proposal": None,
            "market": {
                "volume_24h": 150_000.0,
                "volatility_30d": 0.03,
            },
            "latest_audit": {"details": "insufficient_net_edge_after_costs"},
        },
        {
            "at": "2026-06-03T13:31:40+00:00",
            "watch_status": "EVALUATED",
            "order_proposal": None,
            "market": {
                "volume_24h": 50_000.0,
                "volatility_30d": 0.03,
            },
            "latest_audit": {"details": "insufficient_liquidity"},
        },
    ]

    report = paper_proposal_blocker_report.build_proposal_blocker_report(events)

    assert report["status"] == "PAPER-PROPOSAL-BLOCKER-READY"
    assert report["liquidity_pass_count"] == 1
    assert report["proposal_count"] == 0
    assert report["required_edge_bps"] == 9.0
    assert report["edge_values_min"] == 5.04
    assert report["edge_shortfall_min"] == 3.96
    assert report["auto_submit_enabled"] is False
    assert report["live_trading_approved"] is False


def test_proposal_blocker_markdown_preserves_guardrails():
    report = paper_proposal_blocker_report.build_proposal_blocker_report([])

    markdown = paper_proposal_blocker_report.format_markdown_report(report, "2026-06-04T12:00:00+00:00")

    assert "# Paper Proposal Blocker Report - 2026-06-04" in markdown
    assert "does not change strategy, risk gates, routing, or broker configuration" in markdown
    assert "Auto submit enabled: `False`" in markdown
    assert "Live trading approved: `False`" in markdown
