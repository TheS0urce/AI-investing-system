from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / "logs" / "paper_watch_history.jsonl"
DEFAULT_MIN_VOLUME = 100_000.0


def load_history(path: Path = HISTORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def filter_events(events: list[dict[str, Any]], since: str | None = None) -> list[dict[str, Any]]:
    if since is None:
        return events
    return [item for item in events if str(item.get("at", "")) >= since]


def audit_detail(event: dict[str, Any]) -> str:
    latest_audit = event.get("latest_audit") if isinstance(event.get("latest_audit"), dict) else {}
    return str(latest_audit.get("details", "unknown"))


def market_value(event: dict[str, Any], key: str) -> float | None:
    market = event.get("market") if isinstance(event.get("market"), dict) else {}
    value = market.get(key)
    return value if isinstance(value, int | float) else None


def build_quality_report(
    events: list[dict[str, Any]],
    *,
    since: str | None = None,
    min_volume: float = DEFAULT_MIN_VOLUME,
) -> dict[str, object]:
    filtered = filter_events(events, since)
    evaluated = [item for item in filtered if item.get("watch_status") == "EVALUATED"]
    audit_counts = Counter(audit_detail(item) for item in filtered)
    volumes = [value for item in evaluated if (value := market_value(item, "volume_24h")) is not None]
    spreads = [value for item in evaluated if (value := market_value(item, "spread_bps")) is not None]
    proposals = [item for item in filtered if item.get("order_proposal") is not None]
    first_liquidity_pass = next(
        (
            item.get("at")
            for item in evaluated
            if (market_value(item, "volume_24h") or 0.0) >= min_volume
        ),
        None,
    )
    first_liquidity_block = next(
        (
            item.get("at")
            for item in evaluated
            if audit_detail(item) == "insufficient_liquidity"
        ),
        None,
    )

    return {
        "status": "PAPER-WATCH-QUALITY-READY",
        "scope": "read_only_watch_history_diagnostic",
        "since": since,
        "min_volume": min_volume,
        "total_events": len(filtered),
        "evaluated_events": len(evaluated),
        "proposal_count": len(proposals),
        "audit_details": dict(sorted(audit_counts.items())),
        "first_liquidity_pass_at": first_liquidity_pass,
        "first_liquidity_block_at": first_liquidity_block,
        "volume_min": min(volumes) if volumes else None,
        "volume_max": max(volumes) if volumes else None,
        "spread_bps_max": max(spreads) if spreads else None,
        "auto_submit_enabled": False,
        "live_trading_approved": False,
        "conclusion": (
            "Paper watch ran without proposals. Liquidity was intermittent or still accumulating during the open-window sample; ticks that passed market gates were blocked by net edge after costs."
            if audit_counts.get("insufficient_liquidity") and audit_counts.get("insufficient_net_edge_after_costs")
            else "Paper watch history reviewed without enabling routing or submission."
        ),
    }


def format_markdown_report(report: dict[str, object], generated_at: str) -> str:
    audit_details = report.get("audit_details") if isinstance(report.get("audit_details"), dict) else {}
    audit_lines = [f"- {key}: `{value}`" for key, value in audit_details.items()] or ["- none: `0`"]
    return "\n".join(
        [
            f"# Paper Watch Quality Report - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This report diagnoses read-only paper watch history. It does not submit orders or enable live routing.",
            "",
            "## Totals",
            "",
            f"- Generated at: `{generated_at}`",
            f"- Since: `{report.get('since')}`",
            f"- Total events: `{report.get('total_events')}`",
            f"- Evaluated events: `{report.get('evaluated_events')}`",
            f"- Proposal count: `{report.get('proposal_count')}`",
            f"- Auto submit enabled: `{report.get('auto_submit_enabled')}`",
            f"- Live trading approved: `{report.get('live_trading_approved')}`",
            "",
            "## Market Data",
            "",
            f"- Min volume threshold: `{report.get('min_volume')}`",
            f"- First liquidity pass: `{report.get('first_liquidity_pass_at')}`",
            f"- First liquidity block: `{report.get('first_liquidity_block_at')}`",
            f"- Volume min / max: `{report.get('volume_min')}` / `{report.get('volume_max')}`",
            f"- Max spread bps: `{report.get('spread_bps_max')}`",
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
    return ROOT / f"PAPER_WATCH_QUALITY_REPORT_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose paper watch history quality.")
    parser.add_argument("--since", default=None, help="Only include events at or after this ISO timestamp.")
    parser.add_argument("--min-volume", type=float, default=DEFAULT_MIN_VOLUME)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    report = build_quality_report(load_history(), since=args.since, min_volume=args.min_volume)
    if args.write_report or args.output is not None:
        generated_at = datetime.now(timezone.utc).isoformat()
        output_path = args.output or default_output_path(generated_at)
        output_path.write_text(format_markdown_report(report, generated_at), encoding="utf-8")
        print(json.dumps({"status": "PAPER-WATCH-QUALITY-REPORT-READY", "output": str(output_path)}, indent=2))
        return 0

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
