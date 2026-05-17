from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScalingPolicy:
    reinvest_fraction: float = 0.38
    reserve_fraction: float = 0.62
    roi_tier_1_cap_usd: float = 500.0
    roi_tier_2_cap_usd: float = 1_000.0
    max_strategy_allocation_pct: float = 0.70
    max_external_addition_per_review: float = 50.0


@dataclass(frozen=True)
class ReinvestmentDecision:
    realized_profit: float
    reinvest_amount: float
    reserve_amount: float


@dataclass(frozen=True)
class AllocationDecision:
    tier: str
    low_risk_pct: float
    med_risk_pct: float
    high_risk_pct: float


def compute_reinvestment(realized_profit: float, policy: ScalingPolicy | None = None) -> ReinvestmentDecision:
    """Apply fixed-fraction reinvestment on realized profits only."""
    policy = policy or ScalingPolicy()
    if realized_profit <= 0:
        return ReinvestmentDecision(realized_profit=realized_profit, reinvest_amount=0.0, reserve_amount=0.0)

    reinvest = realized_profit * policy.reinvest_fraction
    reserve = realized_profit * policy.reserve_fraction
    return ReinvestmentDecision(realized_profit=realized_profit, reinvest_amount=reinvest, reserve_amount=reserve)


def choose_roi_tier_allocation(cumulative_roi_usd: float) -> AllocationDecision:
    """Return target risk-bucket allocation from cumulative ROI milestones."""
    if cumulative_roi_usd < 500:
        return AllocationDecision(tier="accumulation", low_risk_pct=1.0, med_risk_pct=0.0, high_risk_pct=0.0)
    if cumulative_roi_usd < 1_000:
        # Growth phase: bias toward medium-risk / high-return.
        return AllocationDecision(tier="growth", low_risk_pct=0.20, med_risk_pct=0.80, high_risk_pct=0.0)
    return AllocationDecision(tier="optimized", low_risk_pct=0.30, med_risk_pct=0.55, high_risk_pct=0.15)


def cap_strategy_capital(current_strategy_capital: float, equity: float, reinvest_amount: float, external_addition: float,
                         policy: ScalingPolicy | None = None) -> float:
    """Cap strategy capital by policy max allocation and max external top-up."""
    policy = policy or ScalingPolicy()
    bounded_external = min(max(external_addition, 0.0), policy.max_external_addition_per_review)
    proposed = current_strategy_capital + max(reinvest_amount, 0.0) + bounded_external
    return min(proposed, equity * policy.max_strategy_allocation_pct)
