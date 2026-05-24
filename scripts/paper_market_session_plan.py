from __future__ import annotations

import argparse
import json
import os
import urllib.error
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from scripts.paper_ops_snapshot import ROOT, fetch_json, load_dotenv
except ModuleNotFoundError:
    from paper_ops_snapshot import ROOT, fetch_json, load_dotenv


def to_operator_time(value: object, timezone_name: str) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        timezone = ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError):
        return None
    return parsed.astimezone(timezone).isoformat()


def parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def seconds_between(start: object, end: object) -> int | None:
    start_dt = parse_datetime(start)
    end_dt = parse_datetime(end)
    if start_dt is None or end_dt is None:
        return None
    return max(0, int((end_dt - start_dt).total_seconds()))


def format_duration(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def session_plan_from_clock(clock: dict[str, Any], timezone_name: str = "Pacific/Auckland") -> dict[str, Any]:
    is_open = bool(clock.get("is_open", False))
    seconds_until_next_open = seconds_between(clock.get("timestamp"), clock.get("next_open"))
    seconds_until_next_close = seconds_between(clock.get("timestamp"), clock.get("next_close"))
    return {
        "status": "MARKET-OPEN-RUN-WATCH" if is_open else "MARKET-CLOSED-WAIT",
        "market_is_open": is_open,
        "clock_timestamp": clock.get("timestamp"),
        "next_open": clock.get("next_open"),
        "next_close": clock.get("next_close"),
        "seconds_until_next_open": seconds_until_next_open,
        "seconds_until_next_close": seconds_until_next_close,
        "time_until_next_open": format_duration(seconds_until_next_open),
        "time_until_next_close": format_duration(seconds_until_next_close),
        "operator_timezone": timezone_name,
        "clock_timestamp_operator": to_operator_time(clock.get("timestamp"), timezone_name),
        "next_open_operator": to_operator_time(clock.get("next_open"), timezone_name),
        "next_close_operator": to_operator_time(clock.get("next_close"), timezone_name),
        "recommended_command": ".venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 60 --iterations 30"
        if is_open
        else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan the next paper watch session from the Alpaca paper clock.")
    parser.add_argument("--timezone", default=os.getenv("AI_OPERATOR_TIMEZONE", "Pacific/Auckland"))
    args = parser.parse_args()

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
    plan = session_plan_from_clock(clock, timezone_name=args.timezone)
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
