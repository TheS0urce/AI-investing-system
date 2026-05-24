from __future__ import annotations

import argparse
import json
import os
import urllib.error
from typing import Any

from paper_ops_snapshot import ROOT, fetch_json, load_dotenv


def failed_readiness_checks(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    checks = readiness.get("checks") if isinstance(readiness.get("checks"), list) else []
    return [item for item in checks if isinstance(item, dict) and item.get("status") != "PASS"]


def summarize_preflight(
    *,
    session_plan: dict[str, Any],
    readiness: dict[str, Any],
    strategy_quality: dict[str, Any],
    open_orders: list[Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if session_plan.get("status") != "MARKET-OPEN-RUN-WATCH":
        reasons.append(f"session_plan={session_plan.get('status')}")
    if readiness.get("status") != "PAPER-GO":
        reasons.append(f"readiness={readiness.get('status')}")
    failed_checks = failed_readiness_checks(readiness)
    reasons.extend(f"{item.get('name')}={item.get('status')}" for item in failed_checks)
    if strategy_quality.get("status") != "STRATEGY-QUALITY-OK":
        reasons.append(f"strategy_quality={strategy_quality.get('status')}")
    if open_orders:
        reasons.append(f"open_orders={len(open_orders)}")

    return {
        "status": "PAPER-MARKET-OPEN-GO" if not reasons else "PAPER-MARKET-OPEN-NO-GO",
        "reasons": reasons,
        "session_plan_status": session_plan.get("status"),
        "market_is_open": session_plan.get("market_is_open"),
        "next_open": session_plan.get("next_open"),
        "next_close": session_plan.get("next_close"),
        "operator_timezone": session_plan.get("operator_timezone"),
        "next_open_operator": session_plan.get("next_open_operator"),
        "next_close_operator": session_plan.get("next_close_operator"),
        "readiness_status": readiness.get("status"),
        "failed_readiness_checks": failed_checks,
        "strategy_quality_status": strategy_quality.get("status"),
        "open_orders": len(open_orders),
        "recommended_command": session_plan.get("recommended_command"),
        "auto_submit_enabled": False,
        "live_trading_approved": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the paper market-open preflight gate.")
    parser.add_argument("--watch-limit", type=int, default=500)
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
        session_plan = fetch_json(api_base, "/broker/paper/session_plan", api_key)
        readiness = fetch_json(api_base, f"/broker/paper/readiness?watch_limit={args.watch_limit}", api_key)
        strategy_quality = fetch_json(api_base, "/broker/paper/strategy_quality", api_key)
        open_orders = fetch_json(api_base, "/broker/paper/orders?status=open&limit=20", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1

    result = summarize_preflight(
        session_plan=session_plan,
        readiness=readiness,
        strategy_quality=strategy_quality,
        open_orders=open_orders if isinstance(open_orders, list) else [],
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PAPER-MARKET-OPEN-GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
