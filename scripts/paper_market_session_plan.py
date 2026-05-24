from __future__ import annotations

import argparse
import json
import os
import urllib.error
from typing import Any

from paper_ops_snapshot import fetch_json, load_dotenv, ROOT


def session_plan_from_clock(clock: dict[str, Any]) -> dict[str, Any]:
    is_open = bool(clock.get("is_open", False))
    return {
        "status": "MARKET-OPEN-RUN-WATCH" if is_open else "MARKET-CLOSED-WAIT",
        "market_is_open": is_open,
        "clock_timestamp": clock.get("timestamp"),
        "next_open": clock.get("next_open"),
        "next_close": clock.get("next_close"),
        "recommended_command": ".venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 60 --iterations 30"
        if is_open
        else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan the next paper watch session from the Alpaca paper clock.")
    parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        payload = fetch_json(api_base, "/broker/paper/clock", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1

    clock = payload.get("clock") if isinstance(payload.get("clock"), dict) else {}
    plan = session_plan_from_clock(clock)
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
