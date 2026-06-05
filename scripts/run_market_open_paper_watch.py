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
DEFAULT_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]


def parse_symbols(raw_symbols: str | None, fallback_symbol: str) -> list[str]:
    raw = raw_symbols if raw_symbols is not None else fallback_symbol
    symbols = [item.strip().upper() for item in raw.split(",") if item.strip()]
    deduped = list(dict.fromkeys(symbols))
    if not deduped:
        raise ValueError("symbols_required")
    if len(deduped) > 20:
        raise ValueError("symbols_limit_20")
    invalid = [symbol for symbol in deduped if not symbol.replace(".", "").replace("-", "").isalnum()]
    if invalid:
        raise ValueError(f"invalid_symbols:{','.join(invalid)}")
    return deduped


def market_closed_wait(preflight: dict[str, object]) -> bool:
    reasons = preflight.get("reasons")
    return (
        preflight.get("status") == "PAPER-MARKET-OPEN-NO-GO"
        and isinstance(reasons, list)
        and "session_plan=MARKET-CLOSED-WAIT" in reasons
    )


def fetch_market_open_preflight(api_base: str, api_key: str) -> dict[str, object]:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/broker/paper/market_open_preflight",
        headers={"X-API-Key": api_key},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_market_open_preflight(
    *,
    api_base: str,
    api_key: str,
    attempts: int,
    retry_delay_seconds: float,
    fetch_preflight: Callable[[str, str], dict[str, object]] = fetch_market_open_preflight,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    latest: dict[str, object] = {}
    for attempt in range(1, attempts + 1):
        latest = fetch_preflight(api_base, api_key)
        print(json.dumps({"status": "PREFLIGHT-CHECK", "attempt": attempt, "preflight": latest}))
        if latest.get("status") == "PAPER-MARKET-OPEN-GO":
            return latest
        if not market_closed_wait(latest) or attempt == attempts:
            return latest
        sleep(retry_delay_seconds)
    return latest


def run_guarded_watch(
    *,
    api_base: str,
    api_key: str,
    symbol: str,
    feed: str,
    interval_seconds: float,
    iterations: int,
    preflight: dict[str, object],
    post_tick: Callable[[str, str, str, str, bool], dict[str, object]] = post_watch_tick,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    if preflight.get("status") != "PAPER-MARKET-OPEN-GO":
        print(
            json.dumps(
                {
                    "status": "PAPER-WATCH-NO-GO",
                    "reason": "market_open_preflight_failed",
                    "preflight": preflight,
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
                "preflight_status": preflight.get("status"),
            }
        )
    )
    for index in range(iterations):
        event = post_tick(api_base, api_key, symbol, feed, False)
        print(json.dumps({"status": "WATCH-TICK-OK", "iteration": index + 1, "event": event}))
        if index < iterations - 1:
            sleep(interval_seconds)
    return 0


def run_guarded_watchlist(
    *,
    api_base: str,
    api_key: str,
    symbols: list[str],
    feed: str,
    interval_seconds: float,
    iterations: int,
    preflight: dict[str, object],
    post_tick: Callable[[str, str, str, str, bool], dict[str, object]] = post_watch_tick,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    if len(symbols) == 1:
        return run_guarded_watch(
            api_base=api_base,
            api_key=api_key,
            symbol=symbols[0],
            feed=feed,
            interval_seconds=interval_seconds,
            iterations=iterations,
            preflight=preflight,
            post_tick=post_tick,
            sleep=sleep,
        )
    if preflight.get("status") != "PAPER-MARKET-OPEN-GO":
        print(
            json.dumps(
                {
                    "status": "PAPER-WATCHLIST-NO-GO",
                    "reason": "market_open_preflight_failed",
                    "preflight": preflight,
                }
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "PAPER-WATCHLIST-RUNNING",
                "symbols": symbols,
                "feed": feed,
                "interval_seconds": interval_seconds,
                "iterations": iterations,
                "ticks_planned": len(symbols) * iterations,
                "auto_submit_enabled": False,
                "preflight_status": preflight.get("status"),
            }
        )
    )
    for cycle_index in range(iterations):
        for symbol in symbols:
            event = post_tick(api_base, api_key, symbol, feed, False)
            print(
                json.dumps(
                    {
                        "status": "WATCHLIST-TICK-OK",
                        "cycle": cycle_index + 1,
                        "symbol": symbol,
                        "event": event,
                    }
                )
            )
        if cycle_index < iterations - 1:
            sleep(interval_seconds)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run paper watch only when the paper market is open.")
    parser.add_argument("--symbol", default="QQQ")
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--preflight-attempts", type=int, default=3)
    parser.add_argument("--preflight-retry-delay-seconds", type=float, default=300.0)
    args = parser.parse_args()

    try:
        symbols = parse_symbols(args.symbols, args.symbol)
    except ValueError as exc:
        print(json.dumps({"status": "NO-GO", "reason": str(exc)}))
        return 1
    if args.interval_seconds < 5:
        print(json.dumps({"status": "NO-GO", "reason": "interval_seconds_must_be_at_least_5"}))
        return 1
    if args.iterations <= 0 or args.iterations > 500:
        print(json.dumps({"status": "NO-GO", "reason": "iterations_must_be_between_1_and_500"}))
        return 1
    if args.preflight_attempts <= 0 or args.preflight_attempts > 10:
        print(json.dumps({"status": "NO-GO", "reason": "preflight_attempts_must_be_between_1_and_10"}))
        return 1
    if args.preflight_retry_delay_seconds < 0:
        print(json.dumps({"status": "NO-GO", "reason": "preflight_retry_delay_seconds_must_be_non_negative"}))
        return 1

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        preflight = wait_for_market_open_preflight(
            api_base=api_base,
            api_key=api_key,
            attempts=args.preflight_attempts,
            retry_delay_seconds=args.preflight_retry_delay_seconds,
        )
        return run_guarded_watchlist(
            api_base=api_base,
            api_key=api_key,
            symbols=symbols,
            feed=args.feed,
            interval_seconds=args.interval_seconds,
            iterations=args.iterations,
            preflight=preflight,
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
