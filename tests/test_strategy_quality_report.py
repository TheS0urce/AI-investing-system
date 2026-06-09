import importlib.util
import sys
from pathlib import Path

from src.ai_investing.config import CostConfig, SystemConfig


SPEC = importlib.util.spec_from_file_location(
    "strategy_quality_report",
    Path(__file__).resolve().parents[1] / "scripts" / "strategy_quality_report.py",
)
strategy_quality_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["strategy_quality_report"] = strategy_quality_report
SPEC.loader.exec_module(strategy_quality_report)


def test_strategy_quality_report_passes_after_edge_model_improvement():
    report = strategy_quality_report.build_strategy_quality_report()

    assert report.status == "STRATEGY-QUALITY-OK"
    assert report.max_theoretical_edge_bps == 14.0
    assert report.required_edge_bps == 9.0
    assert report.edge_shortfall_bps == 0.0
    assert report.min_intraday_signal_bps == 70.0
    assert report.intraday_bps_per_full_conviction == 110.0
    assert report.conclusion == "current_strategy_can_pass_net_edge_gate"


def test_strategy_quality_report_can_pass_with_lower_cost_assumption():
    config = SystemConfig(costs=CostConfig(fee_bps=1.0, slippage_bps=4.0, min_net_edge_bps=2.0))

    report = strategy_quality_report.build_strategy_quality_report(config)

    assert report.status == "STRATEGY-QUALITY-OK"
    assert report.required_edge_bps == 7.0
    assert report.edge_shortfall_bps == 0.0
