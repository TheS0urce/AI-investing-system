from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from run_paper_watch import load_dotenv, post_watch_tick


ROOT = Path(__file__).resolve().parents[1]


def fetch_session_plan(api_base: str, api_key: str) -> dict[str, object]:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/broker/paper/session_plan",
        headers={"X-API-Key": api_key},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def run_guarded_watch(
    *,
    api_base: str,
    api_key: str,
    symbol: str,
    feed: str,
    interval_seconds: float,
    iterations: int,
    session_plan: dict[str, object],
    post_tick: Callable[[str, str, str, str, bool], dict[str, object]] = post_watch_tick,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    if session_plan.get("status") != "MARKET-OPEN-RUN-WATCH":
        print(
            json.dumps(
                {
                    "status": "PAPER-WATCH-NO-GO",
                    "reason": "market_not_open",
                    "session_plan": session_plan,
                }
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "PAPER-WATCH-RUNNING",
                "symbol": symbol,
                "feed": feed,
                "interval_seconds": interval_seconds,
                "iterations": iterations,
                "auto_submit_enabled": False,
            }
        )
    )
    for index in range(iterations):
        event = post_tick(api_base, api_key, symbol, feed, False)
        print(json.dumps({"status": "WATCH-TICK-OK", "iteration": index + 1, "event": event}))
        if index < iterations - 1:
            sleep(interval_seconds)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run paper watch only when the paper market is open.")
    parser.add_argument("--symbol", default="QQQ")
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--iterations", type=int, default=30)
    args = parser.parse_args()

    if args.interval_seconds < 5:
        print(json.dumps({"status": "NO-GO", "reason": "interval_seconds_must_be_at_least_5"}))
        return 1
    if args.iterations <= 0 or args.iterations > 500:
        print(json.dumps({"status": "NO-GO", "reason": "iterations_must_be_between_1_and_500"}))
        return 1

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        session_plan = fetch_session_plan(api_base, api_key)
        return run_guarded_watch(
            api_base=api_base,
            api_key=api_key,
            symbol=args.symbol.upper(),
            feed=args.feed,
            interval_seconds=args.interval_seconds,
            iterations=args.iterations,
            session_plan=session_plan,
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
