from __future__ import annotations

import argparse
import json
import os
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_ops_snapshot import ROOT, fetch_json, load_dotenv


def format_counts(counts: dict[str, Any]) -> list[str]:
    if not counts:
        return ["- none: `0`"]
    return [f"- {key}: `{value}`" for key, value in sorted(counts.items())]


def format_watch_report(summary: dict[str, Any], generated_at: str) -> str:
    return "\n".join(
        [
            f"# Paper Watch Report - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This report summarizes paper watch-mode evidence. Watch mode is read-only and does not submit orders.",
            "",
            "## Totals",
            "",
            f"- Generated at: `{generated_at}`",
            f"- Total ticks: `{summary.get('total_ticks', 0)}`",
            f"- Proposals: `{summary.get('proposal_count', 0)}`",
            f"- Blocked or no proposal: `{summary.get('blocked_or_no_proposal_count', 0)}`",
            f"- Auto submit enabled: `{summary.get('auto_submit_enabled', 'unknown')}`",
            "",
            "## Watch Statuses",
            "",
            *format_counts(summary.get("watch_statuses") if isinstance(summary.get("watch_statuses"), dict) else {}),
            "",
            "## Symbols",
            "",
            *format_counts(summary.get("symbols") if isinstance(summary.get("symbols"), dict) else {}),
            "",
            "## Feeds",
            "",
            *format_counts(summary.get("feeds") if isinstance(summary.get("feeds"), dict) else {}),
            "",
            "## Audit Events",
            "",
            *format_counts(summary.get("audit_events") if isinstance(summary.get("audit_events"), dict) else {}),
            "",
            "## Audit Details",
            "",
            *format_counts(summary.get("audit_details") if isinstance(summary.get("audit_details"), dict) else {}),
            "",
            "## Operator Conclusion",
            "",
            "Paper watch evidence has been summarized without enabling live routing or paper auto-submit.",
            "",
        ]
    )


def default_output_path(generated_at: str) -> Path:
    return ROOT / f"PAPER_WATCH_REPORT_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a paper watch-mode report from local watch history.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.limit <= 0 or args.limit > 5_000:
        print(json.dumps({"status": "NO-GO", "reason": "limit_must_be_between_1_and_5000"}))
        return 1

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        summary = fetch_json(api_base, f"/broker/paper/watch_summary?limit={args.limit}", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1

    generated_at = datetime.now(timezone.utc).isoformat()
    output_path = args.output or default_output_path(generated_at)
    output_path.write_text(format_watch_report(summary, generated_at), encoding="utf-8")

    result = {
        "status": "PAPER-WATCH-REPORT-READY",
        "output": str(output_path),
        "total_ticks": summary.get("total_ticks", 0),
        "proposal_count": summary.get("proposal_count", 0),
        "watch_statuses": summary.get("watch_statuses", {}),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
