from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_watch_quality_report import HISTORY_PATH, ROOT, audit_detail, load_history, market_value


def filter_events(events: list[dict[str, Any]], since: str | None) -> list[dict[str, Any]]:
    if since is None:
        return events
    return [item for item in events if str(item.get("at", "")) >= since]


def count_liquidity_passes(events: list[dict[str, Any]], thresholds: list[float]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for threshold in thresholds:
        counts[str(threshold)] = sum(
            1
            for item in events
            if (market_value(item, "volume_24h") or 0.0) >= threshold
        )
    return counts


def build_liquidity_gate_report(
    events: list[dict[str, Any]],
    *,
    since: str | None = None,
    thresholds: list[float] | None = None,
) -> dict[str, object]:
    thresholds = thresholds or [25_000.0, 50_000.0, 75_000.0, 100_000.0]
    filtered = filter_events(events, since)
    evaluated = [item for item in filtered if item.get("watch_status") == "EVALUATED"]
    audit_counts = Counter(audit_detail(item) for item in evaluated)
    volumes = [value for item in evaluated if (value := market_value(item, "volume_24h")) is not None]
    return {
        "status": "PAPER-LIQUIDITY-GATE-REPORT-READY",
        "scope": "read_only_threshold_diagnostic",
        "since": since,
        "evaluated_events": len(evaluated),
        "audit_details": dict(sorted(audit_counts.items())),
        "volume_min": min(volumes) if volumes else None,
        "volume_max": max(volumes) if volumes else None,
        "threshold_pass_counts": count_liquidity_passes(evaluated, thresholds),
        "auto_submit_enabled": False,
        "live_trading_approved": False,
        "conclusion": (
            "Opening-window liquidity blocks are sensitive to the volume threshold and the data source's intraday volume semantics. Treat this as diagnostic evidence only; do not lower risk gates without more paper sessions."
        ),
    }


def format_markdown_report(report: dict[str, object], generated_at: str) -> str:
    audit_details = report.get("audit_details") if isinstance(report.get("audit_details"), dict) else {}
    threshold_counts = report.get("threshold_pass_counts") if isinstance(report.get("threshold_pass_counts"), dict) else {}
    audit_lines = [f"- {key}: `{value}`" for key, value in audit_details.items()] or ["- none: `0`"]
    threshold_lines = [f"- >= {key}: `{value}`" for key, value in threshold_counts.items()] or ["- none: `0`"]
    return "\n".join(
        [
            f"# Paper Liquidity Gate Report - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This report is a read-only liquidity threshold diagnostic. It does not change risk gates, submit orders, or enable live routing.",
            "",
            "## Totals",
            "",
            f"- Generated at: `{generated_at}`",
            f"- Since: `{report.get('since')}`",
            f"- Evaluated events: `{report.get('evaluated_events')}`",
            f"- Auto submit enabled: `{report.get('auto_submit_enabled')}`",
            f"- Live trading approved: `{report.get('live_trading_approved')}`",
            "",
            "## Volume",
            "",
            f"- Volume min / max: `{report.get('volume_min')}` / `{report.get('volume_max')}`",
            "",
            "## Threshold Pass Counts",
            "",
            *threshold_lines,
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
    return ROOT / f"PAPER_LIQUIDITY_GATE_REPORT_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose paper liquidity gate thresholds from local watch history.")
    parser.add_argument("--since", default=None)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    report = build_liquidity_gate_report(load_history(args.history), since=args.since)
    if args.write_report or args.output is not None:
        generated_at = datetime.now(timezone.utc).isoformat()
        output_path = args.output or default_output_path(generated_at)
        output_path.write_text(format_markdown_report(report, generated_at), encoding="utf-8")
        print(json.dumps({"status": "PAPER-LIQUIDITY-GATE-REPORT-READY", "output": str(output_path)}, indent=2))
        return 0

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
