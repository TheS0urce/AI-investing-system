from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def post_watch_tick(api_base: str, api_key: str, symbol: str, feed: str) -> dict[str, object]:
    body = json.dumps({"symbol": symbol, "feed": feed, "use_paper_account": True}).encode("utf-8")
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/broker/paper/watch_tick",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a read-only paper watch loop.")
    parser.add_argument("--symbol", default="QQQ")
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--iterations", type=int, default=5)
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

    for index in range(args.iterations):
        try:
            event = post_watch_tick(api_base, api_key, args.symbol.upper(), args.feed)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")[:500]
            print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
            return 1
        except urllib.error.URLError as exc:
            print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
            return 1

        print(json.dumps({"status": "WATCH-TICK-OK", "iteration": index + 1, "event": event}))
        if index < args.iterations - 1:
            time.sleep(args.interval_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
