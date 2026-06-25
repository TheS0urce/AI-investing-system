from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

from paper_ops_snapshot import ROOT, load_dotenv


def post_json(api_base: str, path: str, api_key: str) -> dict[str, object]:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {"status": "INVALID-PAYLOAD"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check paper protective exits and submit bounded exits if triggered.")
    parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        payload = post_json(api_base, "/broker/paper/protective_exits/check", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1

    print(json.dumps(payload, indent=2))
    return 0 if str(payload.get("status", "")).startswith(("NO-ACTIVE", "MARKET-CLOSED", "PROTECTIVE")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
