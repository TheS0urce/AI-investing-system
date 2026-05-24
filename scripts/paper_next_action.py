from __future__ import annotations

import argparse
import json
import os
import urllib.error
from typing import Any

try:
    from scripts.paper_ops_snapshot import ROOT, fetch_json, load_dotenv
except ModuleNotFoundError:
    from paper_ops_snapshot import ROOT, fetch_json, load_dotenv


def action_from_preflight(preflight: dict[str, Any]) -> dict[str, Any]:
    status = preflight.get("status")
    reasons = preflight.get("reasons") if isinstance(preflight.get("reasons"), list) else []
    if status == "PAPER-MARKET-OPEN-GO":
        action = "RUN_GUARDED_WATCH"
        detail = "Paper market is open and preflight gates passed."
        command = ".venv/bin/python scripts/run_market_open_paper_watch.py --symbol QQQ --feed iex --interval-seconds 60 --iterations 30"
    elif "session_plan=MARKET-CLOSED-WAIT" in reasons:
        action = "WAIT_FOR_MARKET_OPEN"
        detail = (
            f"Next paper market open is {preflight.get('next_open_operator')} "
            f"({preflight.get('time_until_next_open')} from broker clock)."
        )
        command = ".venv/bin/python scripts/paper_market_open_preflight.py"
    else:
        action = "FIX_PREFLIGHT_REASONS"
        detail = "Resolve preflight reasons before running watch mode."
        command = ".venv/bin/python scripts/paper_market_open_preflight.py"

    return {
        "status": "PAPER-NEXT-ACTION-READY",
        "action": action,
        "detail": detail,
        "command": command,
        "preflight_status": status,
        "reasons": reasons,
        "auto_submit_enabled": False,
        "live_trading_approved": False,
        "preflight": preflight,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the next safe paper-trading operator action.")
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
        preflight = fetch_json(api_base, f"/broker/paper/market_open_preflight?watch_limit={args.watch_limit}", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1

    result = action_from_preflight(preflight)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
