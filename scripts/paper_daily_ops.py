from __future__ import annotations

import argparse
import json
import os
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_ops_evidence import default_output_path, format_ops_evidence
from paper_ops_snapshot import ROOT, fetch_json, load_dotenv


def failed_readiness_checks(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    checks = readiness.get("checks") if isinstance(readiness.get("checks"), list) else []
    return [item for item in checks if isinstance(item, dict) and item.get("status") != "PASS"]


def summarize_daily_ops(snapshot: dict[str, Any], evidence_path: Path, generated_at: str) -> dict[str, Any]:
    broker = snapshot.get("broker") if isinstance(snapshot.get("broker"), dict) else {}
    readiness = snapshot.get("readiness") if isinstance(snapshot.get("readiness"), dict) else {}
    drill = snapshot.get("dry_run_drill") if isinstance(snapshot.get("dry_run_drill"), dict) else {}
    failed_checks = failed_readiness_checks(readiness)
    reasons = []
    if snapshot.get("status") != "PAPER-OPS-READY":
        reasons.append(f"snapshot_status={snapshot.get('status')}")
    if failed_checks:
        reasons.extend(f"{item.get('name')}={item.get('status')}" for item in failed_checks)
    if snapshot.get("open_orders"):
        reasons.append(f"open_orders={len(snapshot.get('open_orders', []))}")
    if drill.get("status") != "PAPER-DRILL-READY-NO-SUBMIT":
        reasons.append(f"dry_run_status={drill.get('status')}")

    return {
        "status": "PAPER-DAILY-GO" if snapshot.get("status") == "PAPER-OPS-READY" else "PAPER-DAILY-NO-GO",
        "generated_at": generated_at,
        "evidence": str(evidence_path),
        "snapshot_status": snapshot.get("status"),
        "broker_status": broker.get("status"),
        "broker_mode": broker.get("mode"),
        "live_enabled": broker.get("live_enabled"),
        "readiness_status": readiness.get("status"),
        "open_orders": len(snapshot.get("open_orders", [])),
        "dry_run_status": drill.get("status"),
        "paper_submission_attempted": snapshot.get("paper_submission_attempted"),
        "live_trading_approved": snapshot.get("live_trading_approved"),
        "failed_checks": failed_checks,
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the daily paper operations check and write evidence.")
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

    summary = summarize_daily_ops(snapshot, output_path, generated_at)
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "PAPER-DAILY-GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
