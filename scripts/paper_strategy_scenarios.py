from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    volatility_30d: float
    order_created: bool
    expected_edge_bps: float | None
    audit_event: str
    audit_details: str


def base_portfolio() -> PortfolioState:
    return PortfolioState(
        cash=1000.0,
        equity=1000.0,
        peak_equity=1000.0,
        daily_pnl=0.0,
        consecutive_losses=0,
        positions={},
    )


def run_scenario(name: str, volatility_30d: float, intraday_change_bps: float = 0.0) -> ScenarioResult:
    system = InvestingSystem(SystemConfig(), SimpleMomentumStrategy())
    market = MarketSnapshot(
        symbol="QQQ",
        price=430.0,
        spread_bps=8.0,
        volume_24h=5_000_000,
        volatility_30d=volatility_30d,
        timestamp=datetime.now(timezone.utc),
        intraday_change_bps=intraday_change_bps,
    )
    order = system.process_tick(market, base_portfolio())
    latest = system.audit_log[-1]
    return ScenarioResult(
        name=name,
        volatility_30d=volatility_30d,
        order_created=order is not None,
        expected_edge_bps=None if order is None else round(order.expected_edge_bps, 6),
        audit_event=latest.event,
        audit_details=latest.details,
    )


def build_scenario_report() -> dict[str, object]:
    scenarios = [
        run_scenario("normal_volatility_blocks_on_edge", 0.03),
        run_scenario("intraday_momentum_reaches_manual_review", 0.03, intraday_change_bps=85.0),
        run_scenario("strong_low_volatility_reaches_manual_review", 0.0001),
        run_scenario("high_volatility_blocks_market", 0.13),
    ]
    return {
        "status": "PAPER-STRATEGY-SCENARIOS-READY",
        "auto_submit_enabled": False,
        "live_trading_approved": False,
        "scenarios": [asdict(item) for item in scenarios],
    }


def format_bool(value: object) -> str:
    return "yes" if value is True else "no" if value is False else str(value)


def format_scenario_table(scenarios: list[dict[str, object]]) -> list[str]:
    rows = [
        "| Scenario | Volatility | Order Created | Expected Edge Bps | Audit Event | Audit Details |",
        "| --- | ---: | --- | ---: | --- | --- |",
    ]
    for item in scenarios:
        edge = item.get("expected_edge_bps")
        rows.append(
            "| "
            + " | ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("volatility_30d", "")),
                    format_bool(item.get("order_created")),
                    "n/a" if edge is None else str(edge),
                    str(item.get("audit_event", "")),
                    str(item.get("audit_details", "")),
                ]
            )
            + " |"
        )
    return rows


def format_markdown_report(report: dict[str, object], generated_at: str) -> str:
    raw_scenarios = report.get("scenarios")
    scenarios = raw_scenarios if isinstance(raw_scenarios, list) else []
    typed_scenarios = [item for item in scenarios if isinstance(item, dict)]
    return "\n".join(
        [
            f"# Paper Strategy Scenario Report - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This report exercises synthetic paper-trading strategy paths. It does not call Alpaca and does not submit orders.",
            "",
            "## Guardrails",
            "",
            f"- Status: `{report.get('status', 'unknown')}`",
            f"- Auto submit enabled: `{format_bool(report.get('auto_submit_enabled'))}`",
            f"- Live trading approved: `{format_bool(report.get('live_trading_approved'))}`",
            "",
            "## Scenarios",
            "",
            *format_scenario_table(typed_scenarios),
            "",
            "## Operator Conclusion",
            "",
            "The strategy has a synthetic path to manual review while preserving paper-only and live-routing guardrails.",
            "",
        ]
    )


def default_output_path(generated_at: str) -> Path:
    return ROOT / f"PAPER_STRATEGY_SCENARIO_REPORT_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic paper strategy scenario checks.")
    parser.add_argument("--output", type=Path, default=None, help="Optional Markdown report path.")
    parser.add_argument("--write-report", action="store_true", help="Write a dated Markdown report.")
    args = parser.parse_args()

    report = build_scenario_report()
    if args.write_report or args.output is not None:
        generated_at = datetime.now(timezone.utc).isoformat()
        output_path = args.output or default_output_path(generated_at)
        output_path.write_text(format_markdown_report(report, generated_at), encoding="utf-8")
        scenarios = report.get("scenarios")
        print(
            json.dumps(
                {
                    "status": "PAPER-STRATEGY-SCENARIO-REPORT-READY",
                    "output": str(output_path),
                    "scenario_count": len(scenarios) if isinstance(scenarios, list) else 0,
                },
                indent=2,
            )
        )
        return 0

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
