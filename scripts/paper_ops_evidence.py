from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_ops_snapshot import ROOT, fetch_json, load_dotenv
import os
import urllib.error


def check_statuses(checks: list[dict[str, Any]]) -> str:
    passed = sum(1 for item in checks if item.get("status") == "PASS")
    return f"{passed}/{len(checks)} PASS"


def format_ops_evidence(snapshot: dict[str, Any], generated_at: str) -> str:
    broker = snapshot.get("broker") if isinstance(snapshot.get("broker"), dict) else {}
    policy = snapshot.get("policy") if isinstance(snapshot.get("policy"), dict) else {}
    account = snapshot.get("account") if isinstance(snapshot.get("account"), dict) else {}
    readiness = snapshot.get("readiness") if isinstance(snapshot.get("readiness"), dict) else {}
    drill = snapshot.get("dry_run_drill") if isinstance(snapshot.get("dry_run_drill"), dict) else {}
    watch_summary = readiness.get("watch_summary") if isinstance(readiness.get("watch_summary"), dict) else {}
    checks = readiness.get("checks") if isinstance(readiness.get("checks"), list) else []

    return "\n".join(
        [
            f"# Paper Ops Evidence - {generated_at[:10]}",
            "",
            "## Scope",
            "",
            "This record documents the consolidated read-only paper operations state.",
            "",
            "## Snapshot",
            "",
            f"- Generated at: `{generated_at}`",
            f"- Snapshot status: `{snapshot.get('status', 'unknown')}`",
            f"- Broker status: `{broker.get('status', 'unknown')}`",
            f"- Broker mode: `{broker.get('mode', 'unknown')}`",
            f"- Live routing enabled: `{broker.get('live_enabled', 'unknown')}`",
            f"- Autonomous execution: `{policy.get('autonomous_execution', 'unknown')}`",
            f"- Manual approval required: `{policy.get('manual_approval_required', 'unknown')}`",
            f"- Kill switch active: `{policy.get('kill_switch', 'unknown')}`",
            "",
            "## Paper Account",
            "",
            f"- Status: `{account.get('status', 'unknown')}`",
            f"- Currency: `{account.get('currency', 'unknown')}`",
            f"- Cash: `{account.get('cash', 'unknown')}`",
            f"- Buying power: `{account.get('buying_power', 'unknown')}`",
            f"- Portfolio value: `{account.get('portfolio_value', 'unknown')}`",
            f"- Pattern day trader: `{account.get('pattern_day_trader', 'unknown')}`",
            f"- Account number: `{account.get('account_number_masked', 'masked')}`",
            "",
            "## Safety Evidence",
            "",
            f"- Open paper orders: `{len(snapshot.get('open_orders', []))}`",
            f"- Readiness status: `{readiness.get('status', 'unknown')}`",
            f"- Readiness checks: `{check_statuses(checks)}`",
            f"- Watch ticks reviewed: `{watch_summary.get('total_ticks', 0)}`",
            f"- Watch proposals: `{watch_summary.get('proposal_count', 0)}`",
            f"- Dry-run drill status: `{drill.get('status', 'unknown')}`",
            f"- Dry-run submit attempted: `{drill.get('submit_attempted', 'unknown')}`",
            f"- Paper submission attempted: `{snapshot.get('paper_submission_attempted', 'unknown')}`",
            f"- Live trading approved: `{snapshot.get('live_trading_approved', 'unknown')}`",
            "",
            "## Operator Conclusion",
            "",
            "The system remains in paper mode with live routing disabled. This evidence does not approve live trading.",
            "",
        ]
    )


def default_output_path(generated_at: str) -> Path:
    return ROOT / f"PAPER_OPS_EVIDENCE_{generated_at[:10]}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a sanitized paper operations evidence report.")
    parser.add_argument("--watch-limit", type=int, default=500)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.watch_limit <= 0 or args.watch_limit > 5_000:
        print(json.dumps({"status": "NO-GO", "reason": "watch_limit_must_be_between_1_and_5000"}))
        return 1

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        snapshot = fetch_json(api_base, f"/broker/paper/ops_snapshot?watch_limit={args.watch_limit}", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1

    generated_at = datetime.now(timezone.utc).isoformat()
    output_path = args.output or default_output_path(generated_at)
    output_path.write_text(format_ops_evidence(snapshot, generated_at), encoding="utf-8")

    print(json.dumps({"status": snapshot.get("status"), "output": str(output_path)}, indent=2))
    return 0 if snapshot.get("status") == "PAPER-OPS-READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
