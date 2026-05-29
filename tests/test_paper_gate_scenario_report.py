import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_gate_scenario_report", SCRIPTS_DIR / "paper_gate_scenario_report.py")
paper_gate_scenario_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["paper_gate_scenario_report"] = paper_gate_scenario_report
SPEC.loader.exec_module(paper_gate_scenario_report)


def test_gate_scenario_replays_candidate_volume_thresholds():
    events = [
        {
            "at": "2026-05-29T13:31:00+00:00",
            "watch_status": "EVALUATED",
            "symbol": "QQQ",
            "market": {
                "symbol": "QQQ",
                "price": 741.0,
                "spread_bps": 1.0,
                "volume_24h": 75_000.0,
                "volatility_30d": 0.03,
                "timestamp": "2026-05-29T13:31:00+00:00",
            },
        },
    ]

    report = paper_gate_scenario_report.build_gate_scenario_report(events, thresholds=[100_000.0, 50_000.0])
    scenarios = {item["min_volume"]: item for item in report["scenarios"]}

    assert report["status"] == "PAPER-GATE-SCENARIOS-READY"
    assert report["auto_submit_enabled"] is False
    assert report["live_trading_approved"] is False
    assert scenarios[100_000.0]["audit_details"] == {"insufficient_liquidity": 1}
    assert scenarios[50_000.0]["audit_details"] == {"insufficient_net_edge_after_costs": 1}
    assert scenarios[50_000.0]["proposal_count"] == 0


def test_gate_scenario_markdown_preserves_guardrails():
    report = paper_gate_scenario_report.build_gate_scenario_report([], thresholds=[100_000.0])

    markdown = paper_gate_scenario_report.format_markdown_report(report, "2026-05-30T12:00:00+00:00")

    assert "# Paper Gate Scenario Report - 2026-05-30" in markdown
    assert "does not change live code paths, submit orders, or enable live routing" in markdown
    assert "Auto submit enabled: `False`" in markdown
    assert "Live trading approved: `False`" in markdown
