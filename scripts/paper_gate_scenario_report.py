from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_watch_quality_report import HISTORY_PATH, ROOT, load_history

sys.path.insert(0, str(ROOT))

from src.ai_investing.config import RiskConfig, SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem


def parse_market(event: dict[str, Any]) -> MarketSnapshot | None:
    market = event.get("market") if isinstance(event.get("market"), dict) else {}
    try:
        timestamp = datetime.fromisoformat(str(market.get("timestamp", event.get("at"))).replace("Z", "+00:00"))
        return MarketSnapshot(
            symbol=str(market.get("symbol", event.get("symbol", "QQQ"))),
            price=float(market.get("price", 0.0)),
            spread_bps=float(market.get("spread_bps", 0.0)),
            volume_24h=float(market.get("volume_24h", 0.0)),
            volatility_30d=float(market.get("volatility_30d", 0.03)),
            timestamp=timestamp,
        )
    except (TypeError, ValueError):
        return None


def base_portfolio() -> PortfolioState:
    return PortfolioState(
        cash=1000.0,
        equity=1000.0,
        peak_equity=1000.0,
        daily_pnl=0.0,
        consecutive_losses=0,
        positions={},
    )


def filter_events(events: list[dict[str, Any]], since: str | None) -> list[dict[str, Any]]:
    if since is None:
        return events
    return [item for item in events if str(item.get("at", "")) >= since]


def replay_threshold(events: list[dict[str, Any]], min_volume: float) -> dict[str, object]:
    config = SystemConfig(risk=RiskConfig(min_volume_24h=min_volume))
    counts: Counter[str] = Counter()
    proposals = 0
    evaluated = 0
    for event in events:
        if event.get("watch_status") != "EVALUATED":
            continue
        market = parse_market(event)
        if market is None:
            counts["invalid_market"] += 1
            continue
        system = InvestingSystem(config, SimpleMomentumStrategy())
        order = system.process_tick(market, base_portfolio())
        evaluated += 1
        if order is not None:
            proposals += 1
        elif system.audit_log:
            counts[system.audit_log[-1].details] += 1
        else:
            counts["unknown"] += 1
    return {
        "min_volume": min_volume,
        "evaluated_events": evaluated,
        "proposal_count": proposals,
        "audit_details": dict(sorted(counts.items())),
    }


def build_gate_scenario_report(
    events: list[dict[str, Any]],
    *,
    since: str | None = None,
    thresholds: list[float] | None = None,
) -> dict[str, object]:
    thresholds = thresholds or [100_000.0, 75_000.0, 50_000.0, 25_000.0]
    filtered = filter_events(events, since)
    scenarios = [replay_threshold(filtered, threshold) for threshold in thresholds]
    return {
        "status": "PAPER-GATE-SCENARIOS-READY",
        "scope": "read_only_watch_replay",
        "since": since,
        "auto_submit_enabled": False,
        "live_trading_approved": False,
        "scenarios": scenarios,
        "conclusion": "Liquidity thresholds affect which gate blocks first, but replay still produces no proposals because ticks that pass market gates fail net-edge checks.",
    }


def format_markdown_report(report: dict[str, object], generated_at: str) -> str:
    scenarios = report.get("scenarios") if isinstance(report.get("scenarios"), list) else []
    rows = [
        "| Min Volume | Evaluated | Proposals | Audit Details |",
        "| ---: | ---: | ---: | --- |",
    ]
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        audit_details = item.get("audit_details") if isinstance(item.get("audit_details"), dict) else {}
        audit_summary = ", ".join(f"{key}={value}" for key, value in audit_details.items()) or "none"
        rows.append(
            f"| {item.get('min_volume')} | {item.get('evaluated_events')} | {item.get('proposal_count')} | {audit_summary} |"
        )
    return "\n".join(
        [
            f"# Paper Gate Scenario Report - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This report replays local paper watch history through candidate market gates. It does not change live code paths, submit orders, or enable live routing.",
            "",
            "## Guardrails",
            "",
            f"- Status: `{report.get('status')}`",
            f"- Auto submit enabled: `{report.get('auto_submit_enabled')}`",
            f"- Live trading approved: `{report.get('live_trading_approved')}`",
            "",
            "## Scenarios",
            "",
            *rows,
            "",
            "## Operator Conclusion",
            "",
            str(report.get("conclusion")),
            "",
        ]
    )


def default_output_path(generated_at: str) -> Path:
    return ROOT / f"PAPER_GATE_SCENARIO_REPORT_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay paper watch history through candidate gate scenarios.")
    parser.add_argument("--since", default=None)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    report = build_gate_scenario_report(load_history(args.history), since=args.since)
    if args.write_report or args.output is not None:
        generated_at = datetime.now(timezone.utc).isoformat()
        output_path = args.output or default_output_path(generated_at)
        output_path.write_text(format_markdown_report(report, generated_at), encoding="utf-8")
        print(json.dumps({"status": "PAPER-GATE-SCENARIO-REPORT-READY", "output": str(output_path)}, indent=2))
        return 0

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
