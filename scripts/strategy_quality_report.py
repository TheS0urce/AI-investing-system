from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ai_investing.config import SystemConfig
from src.ai_investing.execution import EXPECTED_EDGE_BPS_PER_CONVICTION


@dataclass(frozen=True)
class StrategyQualityReport:
    status: str
    max_theoretical_conviction: float
    max_theoretical_edge_bps: float
    required_edge_bps: float
    edge_shortfall_bps: float
    default_fee_bps: float
    default_slippage_bps: float
    min_net_edge_bps: float
    conclusion: str


def build_strategy_quality_report(config: SystemConfig | None = None) -> StrategyQualityReport:
    config = config or SystemConfig()
    # SimpleMomentumStrategy conviction is maxed when volatility_30d is zero:
    # conviction = (0.06 - volatility_30d) * 12.
    max_theoretical_conviction = min(1.0, max(-1.0, 0.06 * 12))
    max_theoretical_edge_bps = EXPECTED_EDGE_BPS_PER_CONVICTION * abs(max_theoretical_conviction)
    required_edge_bps = config.costs.fee_bps + config.costs.slippage_bps + config.costs.min_net_edge_bps
    edge_shortfall_bps = max(0.0, required_edge_bps - max_theoretical_edge_bps)
    status = "STRATEGY-QUALITY-OK" if edge_shortfall_bps == 0 else "STRATEGY-QUALITY-IMPROVEMENT-REQUIRED"
    conclusion = (
        "current_strategy_can_pass_net_edge_gate"
        if status == "STRATEGY-QUALITY-OK"
        else "current_strategy_cannot_pass_net_edge_gate_with_default_costs"
    )
    return StrategyQualityReport(
        status=status,
        max_theoretical_conviction=round(max_theoretical_conviction, 6),
        max_theoretical_edge_bps=round(max_theoretical_edge_bps, 6),
        required_edge_bps=round(required_edge_bps, 6),
        edge_shortfall_bps=round(edge_shortfall_bps, 6),
        default_fee_bps=config.costs.fee_bps,
        default_slippage_bps=config.costs.slippage_bps,
        min_net_edge_bps=config.costs.min_net_edge_bps,
        conclusion=conclusion,
    )


def main() -> int:
    report = build_strategy_quality_report()
    print(json.dumps(asdict(report), indent=2))
    return 0 if report.status == "STRATEGY-QUALITY-OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
