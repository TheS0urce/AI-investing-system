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


def request_json(
    api_base: str,
    path: str,
    api_key: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"X-API-Key": api_key}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{api_base.rstrip('/')}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a guarded Alpaca paper order drill.")
    parser.add_argument("--symbol", default="QQQ")
    parser.add_argument("--side", choices=["BUY", "SELL"], default="BUY")
    parser.add_argument("--quantity", type=float, default=0.001)
    parser.add_argument("--limit-price", type=float, default=1.00)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--cancel-after-submit", action="store_true")
    parser.add_argument("--cancel-confirm", default="")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "NO-GO", "reason": "api_key_missing"}))
        return 1

    order = {
        "symbol": args.symbol.upper(),
        "side": args.side,
        "quantity": args.quantity,
        "limit_price": args.limit_price,
        "expected_edge_bps": 0.0,
        "reason": "manual guarded paper order drill",
    }

    try:
        readiness = request_json(api_base, "/broker/paper/readiness?watch_limit=500", api_key)
        open_before = request_json(api_base, "/broker/paper/orders?status=open&limit=20", api_key)
        preview = request_json(api_base, "/broker/paper/order_preview", api_key, method="POST", payload=order)

        result: dict[str, Any] = {
            "status": "PAPER-DRILL-READY-NO-SUBMIT",
            "readiness_status": readiness.get("status"),
            "open_orders_before": open_before,
            "order_preview": preview,
            "submit_attempted": False,
            "cancel_attempted": False,
        }

        if readiness.get("status") != "PAPER-GO":
            result["status"] = "PAPER-DRILL-NO-GO"
            print(json.dumps(result, indent=2))
            return 1

        if not args.submit:
            result["next_required_confirmation"] = "SUBMIT_PAPER_ORDER"
            print(json.dumps(result, indent=2))
            return 0

        if args.confirm != "SUBMIT_PAPER_ORDER":
            result["status"] = "PAPER-DRILL-NO-SUBMIT"
            result["reason"] = "confirmation_phrase_required"
            print(json.dumps(result, indent=2))
            return 1

        submitted = request_json(
            api_base,
            "/broker/paper/submit_order",
            api_key,
            method="POST",
            payload={**order, "confirm": args.confirm},
        )
        result["status"] = "PAPER-DRILL-SUBMITTED"
        result["submit_attempted"] = True
        result["submitted"] = submitted
        result["orders_after_submit"] = request_json(api_base, "/broker/paper/orders?status=all&limit=20", api_key)

        if args.cancel_after_submit:
            if args.cancel_confirm != "CANCEL_PAPER_ORDERS":
                result["status"] = "PAPER-DRILL-CANCEL-NO-GO"
                result["reason"] = "cancel_confirmation_phrase_required"
                print(json.dumps(result, indent=2))
                return 1
            cancelled = request_json(
                api_base,
                "/broker/paper/cancel_orders",
                api_key,
                method="POST",
                payload={"confirm": args.cancel_confirm},
            )
            result["cancel_attempted"] = True
            result["cancelled"] = cancelled

        result["open_orders_after"] = request_json(api_base, "/broker/paper/orders?status=open&limit=20", api_key)
        print(json.dumps(result, indent=2))
        return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "NO-GO", "reason": f"network_error:{exc.reason}"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
