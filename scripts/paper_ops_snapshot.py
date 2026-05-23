from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


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


def fetch_json(api_base: str, path: str, api_key: str) -> Any:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        headers={"X-API-Key": api_key},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the consolidated read-only paper operations snapshot.")
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
        snapshot = fetch_json(api_base, f"/broker/paper/ops_snapshot?watch_limit={args.watch_limit}", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1

    print(json.dumps(snapshot, indent=2))
    return 0 if snapshot.get("status") == "PAPER-OPS-READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
