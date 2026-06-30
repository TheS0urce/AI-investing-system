from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from run_market_open_paper_watch import parse_symbols
from run_paper_watch import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


def request_json(
    api_base: str,
    api_key: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("live_api_invalid_payload")
    return result


def proposal_request(event: dict[str, Any]) -> dict[str, Any] | None:
    proposal = event.get("order_proposal")
    market = event.get("market")
    if not isinstance(proposal, dict) or not isinstance(market, dict):
        return None
    return {
        "symbol": proposal.get("symbol"),
        "side": proposal.get("side"),
        "quantity": proposal.get("quantity"),
        "limit_price": proposal.get("limit_price"),
        "expected_edge_bps": proposal.get("expected_edge_bps"),
        "reason": proposal.get("reason"),
        "spread_bps": market.get("spread_bps"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded live watch under an active live lease.")
    parser.add_argument("--symbols", default="QQQ,NVDA,MSFT")
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    parser.add_argument("--iterations", type=int, default=90)
    parser.add_argument("--max-submits", type=int, default=2)
    args = parser.parse_args()

    try:
        symbols = parse_symbols(args.symbols, "QQQ")
    except ValueError as exc:
        print(json.dumps({"status": "LIVE-NO-GO", "reason": str(exc)}))
        return 1
    if args.interval_seconds < 5:
        print(json.dumps({"status": "LIVE-NO-GO", "reason": "interval_seconds_must_be_at_least_5"}))
        return 1
    if args.iterations <= 0 or args.iterations > 500:
        print(json.dumps({"status": "LIVE-NO-GO", "reason": "iterations_must_be_between_1_and_500"}))
        return 1
    if args.max_submits <= 0 or args.max_submits > 2:
        print(json.dumps({"status": "LIVE-NO-GO", "reason": "max_submits_must_be_between_1_and_2"}))
        return 1

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "LIVE-NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        authorization = request_json(api_base, api_key, "/broker/live/authorization")
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as exc:
        print(json.dumps({"status": "LIVE-NO-GO", "reason": str(exc)}))
        return 1
    if authorization.get("status") != "ACTIVE":
        print(
            json.dumps(
                {
                    "status": "LIVE-NO-GO",
                    "reason": "bounded_live_authorization_not_active",
                }
            )
        )
        return 1

    submit_attempts = 0
    for cycle in range(1, args.iterations + 1):
        try:
            exits = request_json(
                api_base,
                api_key,
                "/broker/live/protective_exits/check",
                payload={},
            )
            print(json.dumps({"status": "LIVE-PROTECTIVE-EXIT-CHECK", "cycle": cycle, "result": exits}))
            for symbol in symbols:
                event = request_json(
                    api_base,
                    api_key,
                    "/broker/live/watch_tick",
                    payload={
                        "symbol": symbol,
                        "feed": args.feed,
                        "use_paper_account": False,
                    },
                )
                print(
                    json.dumps(
                        {
                            "status": "LIVE-WATCH-TICK-OK",
                            "cycle": cycle,
                            "symbol": symbol,
                            "event": event,
                        }
                    )
                )
                proposal = proposal_request(event)
                if proposal is None or submit_attempts >= args.max_submits:
                    continue
                submit_attempts += 1
                submitted = request_json(
                    api_base,
                    api_key,
                    "/broker/live/authorization/submit",
                    payload=proposal,
                )
                print(
                    json.dumps(
                        {
                            "status": "LIVE-SUBMIT-OK",
                            "cycle": cycle,
                            "symbol": symbol,
                            "result": submitted,
                        }
                    )
                )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")[:500]
            print(
                json.dumps(
                    {
                        "status": "LIVE-WATCH-STOPPED",
                        "reason": f"http_error:{exc.code}:{body}",
                    }
                )
            )
            return 1
        except (urllib.error.URLError, RuntimeError) as exc:
            print(json.dumps({"status": "LIVE-WATCH-STOPPED", "reason": str(exc)}))
            return 1
        if cycle < args.iterations:
            time.sleep(args.interval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
