import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_liquidity_gate_report", SCRIPTS_DIR / "paper_liquidity_gate_report.py")
paper_liquidity_gate_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["paper_liquidity_gate_report"] = paper_liquidity_gate_report
SPEC.loader.exec_module(paper_liquidity_gate_report)


def test_liquidity_gate_report_counts_threshold_passes():
    events = [
        {
            "at": "2026-05-29T13:31:00+00:00",
            "watch_status": "EVALUATED",
            "market": {"volume_24h": 30_000.0},
            "latest_audit": {"details": "insufficient_liquidity"},
        },
        {
            "at": "2026-05-29T13:32:00+00:00",
            "watch_status": "EVALUATED",
            "market": {"volume_24h": 90_000.0},
            "latest_audit": {"details": "insufficient_liquidity"},
        },
        {
            "at": "2026-05-29T13:33:00+00:00",
            "watch_status": "EVALUATED",
            "market": {"volume_24h": 120_000.0},
            "latest_audit": {"details": "insufficient_net_edge_after_costs"},
        },
    ]

    report = paper_liquidity_gate_report.build_liquidity_gate_report(events, thresholds=[50_000.0, 100_000.0])

    assert report["status"] == "PAPER-LIQUIDITY-GATE-REPORT-READY"
    assert report["evaluated_events"] == 3
    assert report["threshold_pass_counts"] == {"50000.0": 2, "100000.0": 1}
    assert report["audit_details"]["insufficient_liquidity"] == 2
    assert report["audit_details"]["insufficient_net_edge_after_costs"] == 1
    assert report["auto_submit_enabled"] is False
    assert report["live_trading_approved"] is False


def test_liquidity_gate_markdown_is_diagnostic_only():
    report = paper_liquidity_gate_report.build_liquidity_gate_report([], since="2026-05-29T13:00:00+00:00")

    markdown = paper_liquidity_gate_report.format_markdown_report(report, "2026-05-30T12:00:00+00:00")

    assert "# Paper Liquidity Gate Report - 2026-05-30" in markdown
    assert "does not change risk gates, submit orders, or enable live routing" in markdown
    assert "Auto submit enabled: `False`" in markdown
    assert "Live trading approved: `False`" in markdown
