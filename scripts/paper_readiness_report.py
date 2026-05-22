from __future__ import annotations

import json
import os
import sys
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


def fetch_json(api_base: str, path: str, api_key: str | None = None) -> Any:
    headers = {"X-API-Key": api_key} if api_key else {}
    request = urllib.request.Request(f"{api_base.rstrip('/')}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def check(condition: bool, name: str, detail: str = "") -> dict[str, object]:
    return {
        "name": name,
        "status": "PASS" if condition else "FAIL",
        "detail": detail,
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        health = fetch_json(api_base, "/health")
        summary = fetch_json(api_base, "/dashboard/summary", api_key)
        broker = fetch_json(api_base, "/broker/status", api_key)
        watch_summary = fetch_json(api_base, "/broker/paper/watch_summary?limit=500", api_key)
        open_orders = fetch_json(api_base, "/broker/paper/orders?status=open&limit=20", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1

    checks = [
        check(health.get("status") == "ok", "api_health_ok", str(health)),
        check(summary.get("manual_approval_required") is True, "manual_approval_required"),
        check(summary.get("autonomous_execution") is False, "autonomous_execution_disabled"),
        check(summary.get("kill_switch") is False, "kill_switch_not_active"),
        check(broker.get("provider") == "alpaca", "broker_provider_alpaca"),
        check(broker.get("mode") == "paper", "broker_mode_paper"),
        check(broker.get("live_enabled") is False, "live_routing_disabled"),
        check(broker.get("status") == "ALPACA-PAPER-READY", "broker_paper_ready", broker.get("reason", "")),
        check(isinstance(open_orders, list) and len(open_orders) == 0, "no_open_paper_orders", str(open_orders)),
        check(watch_summary.get("auto_submit_enabled") is False, "watch_auto_submit_disabled"),
        check(watch_summary.get("total_ticks", 0) >= 1, "watch_history_has_evidence"),
    ]
    passed = all(item["status"] == "PASS" for item in checks)
    result = {
        "status": "PAPER-GO" if passed else "PAPER-NO-GO",
        "api_base": api_base,
        "checks": checks,
        "watch_summary": watch_summary,
    }
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
