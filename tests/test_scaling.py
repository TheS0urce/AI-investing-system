import importlib.util
import sys
from pathlib import Path

import pytest

from src.ai_investing.scaling import (
    cap_strategy_capital,
    choose_roi_tier_allocation,
    compute_reinvestment,
)


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("scaling_policy_report", SCRIPTS_DIR / "scaling_policy_report.py")
scaling_policy_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["scaling_policy_report"] = scaling_policy_report
SPEC.loader.exec_module(scaling_policy_report)


def test_reinvestment_splits_realized_profit_by_policy():
    decision = compute_reinvestment(100.0)

    assert decision.realized_profit == 100.0
    assert decision.reinvest_amount == pytest.approx(38.0)
    assert decision.reserve_amount == pytest.approx(62.0)


def test_reinvestment_ignores_non_positive_profit():
    decision = compute_reinvestment(-10.0)

    assert decision.reinvest_amount == 0.0
    assert decision.reserve_amount == 0.0


def test_roi_tier_allocations_match_policy_thresholds():
    accumulation = choose_roi_tier_allocation(499.99)
    growth = choose_roi_tier_allocation(500.0)
    optimized = choose_roi_tier_allocation(1_000.0)

    assert accumulation.tier == "accumulation"
    assert (accumulation.low_risk_pct, accumulation.med_risk_pct, accumulation.high_risk_pct) == (1.0, 0.0, 0.0)
    assert growth.tier == "growth"
    assert (growth.low_risk_pct, growth.med_risk_pct, growth.high_risk_pct) == (0.20, 0.80, 0.0)
    assert optimized.tier == "optimized"
    assert (optimized.low_risk_pct, optimized.med_risk_pct, optimized.high_risk_pct) == (0.30, 0.55, 0.15)


def test_strategy_capital_caps_external_addition_and_total_allocation():
    capped = cap_strategy_capital(
        current_strategy_capital=680.0,
        equity=1_000.0,
        reinvest_amount=38.0,
        external_addition=250.0,
    )

    assert capped == pytest.approx(700.0)


def test_scaling_policy_report_is_guarded_and_deterministic():
    report = scaling_policy_report.build_scaling_policy_report()

    assert report["status"] == "SCALING-POLICY-READY"
    assert report["auto_submit_enabled"] is False
    assert report["live_trading_approved"] is False
    assert report["reinvestment"]["reinvest_amount"] == pytest.approx(38.0)
    assert report["allocation"]["tier"] == "optimized"
    assert report["capped_strategy_capital"] == pytest.approx(588.0)


def test_scaling_policy_markdown_report_summarizes_guardrails():
    report = scaling_policy_report.build_scaling_policy_report()

    markdown = scaling_policy_report.format_markdown_report(report, "2026-05-25T12:00:00+00:00")

    assert "# Scaling Policy Report - 2026-05-25" in markdown
    assert "does not call Alpaca and does not submit orders" in markdown
    assert "- Auto submit enabled: `no`" in markdown
    assert "- Live trading approved: `no`" in markdown
    assert "Scaling remains a governed policy input" in markdown
