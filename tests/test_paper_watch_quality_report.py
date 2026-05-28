import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_watch_quality_report", SCRIPTS_DIR / "paper_watch_quality_report.py")
paper_watch_quality_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["paper_watch_quality_report"] = paper_watch_quality_report
SPEC.loader.exec_module(paper_watch_quality_report)


def test_quality_report_identifies_liquidity_pass_and_edge_blocks():
    events = [
        {
            "at": "2026-05-28T13:31:00+00:00",
            "watch_status": "EVALUATED",
            "market": {"volume_24h": 50_000.0, "spread_bps": 2.0},
            "order_proposal": None,
            "latest_audit": {"details": "insufficient_liquidity"},
        },
        {
            "at": "2026-05-28T13:52:00+00:00",
            "watch_status": "EVALUATED",
            "market": {"volume_24h": 110_000.0, "spread_bps": 1.0},
            "order_proposal": None,
            "latest_audit": {"details": "insufficient_net_edge_after_costs"},
        },
    ]

    report = paper_watch_quality_report.build_quality_report(events, min_volume=100_000.0)

    assert report["status"] == "PAPER-WATCH-QUALITY-READY"
    assert report["proposal_count"] == 0
    assert report["audit_details"]["insufficient_liquidity"] == 1
    assert report["audit_details"]["insufficient_net_edge_after_costs"] == 1
    assert report["first_liquidity_pass_at"] == "2026-05-28T13:52:00+00:00"
    assert report["first_liquidity_block_at"] == "2026-05-28T13:31:00+00:00"
    assert report["volume_min"] == 50_000.0
    assert report["volume_max"] == 110_000.0


def test_quality_markdown_preserves_guardrails():
    report = paper_watch_quality_report.build_quality_report(
        [
            {
                "at": "2026-05-28T13:52:00+00:00",
                "watch_status": "EVALUATED",
                "market": {"volume_24h": 110_000.0, "spread_bps": 1.0},
                "order_proposal": None,
                "latest_audit": {"details": "insufficient_net_edge_after_costs"},
            }
        ],
        since="2026-05-28T13:00:00+00:00",
    )

    markdown = paper_watch_quality_report.format_markdown_report(report, "2026-05-29T12:00:00+00:00")

    assert "# Paper Watch Quality Report - 2026-05-29" in markdown
    assert "does not submit orders or enable live routing" in markdown
    assert "Auto submit enabled: `False`" in markdown
    assert "Live trading approved: `False`" in markdown
