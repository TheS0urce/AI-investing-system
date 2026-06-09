import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("paper_strategy_scenarios", SCRIPTS_DIR / "paper_strategy_scenarios.py")
paper_strategy_scenarios = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["paper_strategy_scenarios"] = paper_strategy_scenarios
SPEC.loader.exec_module(paper_strategy_scenarios)


def test_strategy_scenarios_show_block_and_manual_review_paths():
    report = paper_strategy_scenarios.build_scenario_report()

    assert report["status"] == "PAPER-STRATEGY-SCENARIOS-READY"
    assert report["auto_submit_enabled"] is False
    scenarios = {item["name"]: item for item in report["scenarios"]}
    assert scenarios["normal_volatility_blocks_on_edge"]["audit_details"] == "insufficient_net_edge_after_costs"
    assert scenarios["intraday_momentum_reaches_manual_review"]["order_created"] is True
    assert scenarios["intraday_momentum_reaches_manual_review"]["audit_event"] == "manual_review_required"
    assert scenarios["strong_low_volatility_reaches_manual_review"]["order_created"] is True
    assert scenarios["strong_low_volatility_reaches_manual_review"]["audit_event"] == "manual_review_required"
    assert scenarios["high_volatility_blocks_market"]["audit_details"] == "volatility_too_high"


def test_strategy_scenario_markdown_report_summarizes_guardrails():
    report = paper_strategy_scenarios.build_scenario_report()

    markdown = paper_strategy_scenarios.format_markdown_report(report, "2026-05-24T12:00:00+00:00")

    assert "# Paper Strategy Scenario Report - 2026-05-24" in markdown
    assert "does not submit orders" in markdown
    assert "- Auto submit enabled: `no`" in markdown
    assert "- Live trading approved: `no`" in markdown
    assert "strong_low_volatility_reaches_manual_review" in markdown
    assert "manual_review_required" in markdown
