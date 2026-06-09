from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_watch_quality_report import HISTORY_PATH, ROOT, audit_detail, filter_events, load_history, market_value

sys.path.insert(0, str(ROOT))

from src.ai_investing.config import SystemConfig
from src.ai_investing.execution import EXPECTED_EDGE_BPS_PER_CONVICTION
from src.ai_investing.models import MarketSnapshot
from src.ai_investing.strategy import intraday_momentum_conviction, volatility_proxy_conviction


def expected_edge_bps_from_event(event: dict[str, Any]) -> float | None:
    market = event.get("market") if isinstance(event.get("market"), dict) else {}
    volatility = market_value(event, "volatility_30d")
    if volatility is None:
        return None
    snapshot = MarketSnapshot(
        symbol=str(event.get("symbol", market.get("symbol", "QQQ"))),
        price=float(market.get("price", 1.0) or 1.0),
        spread_bps=float(market.get("spread_bps", 0.0) or 0.0),
        volume_24h=float(market.get("volume_24h", 0.0) or 0.0),
        volatility_30d=volatility,
        timestamp=datetime.now(timezone.utc),
        intraday_change_bps=float(market.get("intraday_change_bps", 0.0) or 0.0),
    )
    conviction = intraday_momentum_conviction(snapshot) or volatility_proxy_conviction(snapshot)
    if conviction is None or abs(conviction) < 0.1:
        return None
    return EXPECTED_EDGE_BPS_PER_CONVICTION * abs(conviction)


def build_proposal_blocker_report(events: list[dict[str, Any]], *, since: str | None = None) -> dict[str, object]:
    config = SystemConfig()
    required_edge_bps = config.costs.fee_bps + config.costs.slippage_bps + config.costs.min_net_edge_bps
    min_volume = config.risk.min_volume_24h
    filtered = filter_events(events, since)
    evaluated = [item for item in filtered if item.get("watch_status") == "EVALUATED"]
    proposals = [item for item in evaluated if item.get("order_proposal") is not None]
    audit_counts = Counter(audit_detail(item) for item in evaluated)
    liquidity_pass = [item for item in evaluated if (market_value(item, "volume_24h") or 0.0) >= min_volume]
    edge_values = [edge for item in liquidity_pass if (edge := expected_edge_bps_from_event(item)) is not None]
    edge_shortfalls = [round(required_edge_bps - edge, 6) for edge in edge_values if edge < required_edge_bps]

    return {
        "status": "PAPER-PROPOSAL-BLOCKER-READY",
        "scope": "read_only_watch_history_diagnostic",
        "since": since,
        "evaluated_events": len(evaluated),
        "proposal_count": len(proposals),
        "audit_details": dict(sorted(audit_counts.items())),
        "min_volume": min_volume,
        "liquidity_pass_count": len(liquidity_pass),
        "required_edge_bps": required_edge_bps,
        "edge_values_min": min(edge_values) if edge_values else None,
        "edge_values_max": max(edge_values) if edge_values else None,
        "edge_shortfall_min": min(edge_shortfalls) if edge_shortfalls else None,
        "edge_shortfall_max": max(edge_shortfalls) if edge_shortfalls else None,
        "auto_submit_enabled": False,
        "live_trading_approved": False,
        "conclusion": (
            "The latest proposal blocker is strategy edge, not execution plumbing: ticks that pass liquidity still fall below the configured net-edge requirement."
            if edge_shortfalls
            else "No edge shortfall was observed in this sample; inspect other safety gates before changing strategy parameters."
        ),
    }


def format_markdown_report(report: dict[str, object], generated_at: str) -> str:
    audit_details = report.get("audit_details") if isinstance(report.get("audit_details"), dict) else {}
    audit_lines = [f"- {key}: `{value}`" for key, value in audit_details.items()] or ["- none: `0`"]
    return "\n".join(
        [
            f"# Paper Proposal Blocker Report - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This report diagnoses why read-only paper watch ticks did not become proposals. It does not change strategy, risk gates, routing, or broker configuration.",
            "",
            "## Guardrails",
            "",
            f"- Auto submit enabled: `{report.get('auto_submit_enabled')}`",
            f"- Live trading approved: `{report.get('live_trading_approved')}`",
            "",
            "## Totals",
            "",
            f"- Since: `{report.get('since')}`",
            f"- Evaluated events: `{report.get('evaluated_events')}`",
            f"- Proposal count: `{report.get('proposal_count')}`",
            f"- Liquidity pass count at current gate: `{report.get('liquidity_pass_count')}`",
            "",
            "## Edge Gap",
            "",
            f"- Required edge bps: `{report.get('required_edge_bps')}`",
            f"- Observed expected edge min / max after liquidity pass: `{report.get('edge_values_min')}` / `{report.get('edge_values_max')}`",
            f"- Edge shortfall min / max: `{report.get('edge_shortfall_min')}` / `{report.get('edge_shortfall_max')}`",
            "",
            "## Audit Details",
            "",
            *audit_lines,
            "",
            "## Operator Conclusion",
            "",
            str(report.get("conclusion")),
            "",
        ]
    )


def default_output_path(generated_at: str) -> Path:
    return ROOT / f"PAPER_PROPOSAL_BLOCKER_REPORT_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose paper watch proposal blockers.")
    parser.add_argument("--since", default=None)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    report = build_proposal_blocker_report(load_history(args.history), since=args.since)
    if args.write_report or args.output is not None:
        generated_at = datetime.now(timezone.utc).isoformat()
        output_path = args.output or default_output_path(generated_at)
        output_path.write_text(format_markdown_report(report, generated_at), encoding="utf-8")
        print(json.dumps({"status": "PAPER-PROPOSAL-BLOCKER-REPORT-READY", "output": str(output_path)}, indent=2))
        return 0

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
