from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai_investing.scaling import (  # noqa: E402
    ScalingPolicy,
    cap_strategy_capital,
    choose_roi_tier_allocation,
    compute_reinvestment,
)


def build_scaling_policy_report(
    realized_profit: float = 100.0,
    cumulative_roi_usd: float = 1_000.0,
    current_strategy_capital: float = 500.0,
    equity: float = 1_000.0,
    external_addition: float = 50.0,
    policy: ScalingPolicy | None = None,
) -> dict[str, object]:
    policy = policy or ScalingPolicy()
    reinvestment = compute_reinvestment(realized_profit, policy)
    allocation = choose_roi_tier_allocation(cumulative_roi_usd)
    capped_strategy_capital = cap_strategy_capital(
        current_strategy_capital=current_strategy_capital,
        equity=equity,
        reinvest_amount=reinvestment.reinvest_amount,
        external_addition=external_addition,
        policy=policy,
    )
    return {
        "status": "SCALING-POLICY-READY",
        "scope": "deterministic_policy_report_only",
        "auto_submit_enabled": False,
        "live_trading_approved": False,
        "policy": asdict(policy),
        "inputs": {
            "realized_profit": realized_profit,
            "cumulative_roi_usd": cumulative_roi_usd,
            "current_strategy_capital": current_strategy_capital,
            "equity": equity,
            "external_addition": external_addition,
        },
        "reinvestment": asdict(reinvestment),
        "allocation": asdict(allocation),
        "capped_strategy_capital": capped_strategy_capital,
    }


def format_bool(value: object) -> str:
    return "yes" if value is True else "no" if value is False else str(value)


def format_markdown_report(report: dict[str, object], generated_at: str) -> str:
    policy = report.get("policy") if isinstance(report.get("policy"), dict) else {}
    inputs = report.get("inputs") if isinstance(report.get("inputs"), dict) else {}
    reinvestment = report.get("reinvestment") if isinstance(report.get("reinvestment"), dict) else {}
    allocation = report.get("allocation") if isinstance(report.get("allocation"), dict) else {}
    return "\n".join(
        [
            f"# Scaling Policy Report - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This report validates deterministic reinvestment and ROI-tier allocation policy only. It does not call Alpaca and does not submit orders.",
            "",
            "## Guardrails",
            "",
            f"- Status: `{report.get('status', 'unknown')}`",
            f"- Auto submit enabled: `{format_bool(report.get('auto_submit_enabled'))}`",
            f"- Live trading approved: `{format_bool(report.get('live_trading_approved'))}`",
            "",
            "## Policy",
            "",
            f"- Reinvest fraction: `{policy.get('reinvest_fraction')}`",
            f"- Reserve fraction: `{policy.get('reserve_fraction')}`",
            f"- Max strategy allocation pct: `{policy.get('max_strategy_allocation_pct')}`",
            f"- Max external addition per review: `{policy.get('max_external_addition_per_review')}`",
            "",
            "## Example Decision",
            "",
            f"- Realized profit: `${inputs.get('realized_profit')}`",
            f"- Reinvest amount: `${reinvestment.get('reinvest_amount')}`",
            f"- Reserve amount: `${reinvestment.get('reserve_amount')}`",
            f"- Cumulative ROI: `${inputs.get('cumulative_roi_usd')}`",
            f"- Allocation tier: `{allocation.get('tier')}`",
            f"- Low / medium / high risk: `{allocation.get('low_risk_pct')}` / `{allocation.get('med_risk_pct')}` / `{allocation.get('high_risk_pct')}`",
            f"- Capped strategy capital: `${report.get('capped_strategy_capital')}`",
            "",
            "## Operator Conclusion",
            "",
            "Scaling remains a governed policy input. It does not increase directional aggression or enable autonomous/live execution.",
            "",
        ]
    )


def default_output_path(generated_at: str) -> Path:
    return ROOT / f"SCALING_POLICY_REPORT_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic scaling policy report.")
    parser.add_argument("--realized-profit", type=float, default=100.0)
    parser.add_argument("--cumulative-roi-usd", type=float, default=1_000.0)
    parser.add_argument("--current-strategy-capital", type=float, default=500.0)
    parser.add_argument("--equity", type=float, default=1_000.0)
    parser.add_argument("--external-addition", type=float, default=50.0)
    parser.add_argument("--output", type=Path, default=None, help="Optional Markdown report path.")
    parser.add_argument("--write-report", action="store_true", help="Write a dated Markdown report.")
    args = parser.parse_args()

    report = build_scaling_policy_report(
        realized_profit=args.realized_profit,
        cumulative_roi_usd=args.cumulative_roi_usd,
        current_strategy_capital=args.current_strategy_capital,
        equity=args.equity,
        external_addition=args.external_addition,
    )
    if args.write_report or args.output is not None:
        generated_at = datetime.now(timezone.utc).isoformat()
        output_path = args.output or default_output_path(generated_at)
        output_path.write_text(format_markdown_report(report, generated_at), encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "SCALING-POLICY-REPORT-READY",
                    "output": str(output_path),
                },
                indent=2,
            )
        )
        return 0

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
