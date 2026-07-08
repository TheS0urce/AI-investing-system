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


def recovery_gate_decision(event: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
    proposal = event.get("order_proposal")
    market = event.get("market")
    if not isinstance(proposal, dict) or not isinstance(market, dict):
        return {"status": "NO_PROPOSAL", "reason": "no_order_proposal"}

    expected_edge_bps = float(proposal.get("expected_edge_bps", 0.0) or 0.0)
    spread_bps = float(market.get("spread_bps", 0.0) or 0.0)
    minimum_expected_edge_bps = float(limits.get("minimum_expected_edge_bps", 0.0) or 0.0)
    max_spread_bps = float(limits.get("max_spread_bps", 0.0) or 0.0)
    gate_pass = expected_edge_bps >= minimum_expected_edge_bps and spread_bps <= max_spread_bps
    reason = "recovery_gate_pass" if gate_pass else "recovery_gate_block"
    if expected_edge_bps < minimum_expected_edge_bps:
        reason = "insufficient_expected_edge"
    elif spread_bps > max_spread_bps:
        reason = "spread_too_wide"

    return {
        "status": "PASS" if gate_pass else "BLOCK",
        "reason": reason,
        "symbol": proposal.get("symbol"),
        "expected_edge_bps": expected_edge_bps,
        "minimum_expected_edge_bps": minimum_expected_edge_bps,
        "spread_bps": spread_bps,
        "max_spread_bps": max_spread_bps,
        "proposal": proposal,
    }


def effective_limits_from_readiness(readiness: dict[str, Any]) -> dict[str, Any]:
    authorization = readiness.get("authorization")
    if not isinstance(authorization, dict):
        return {}
    limits = authorization.get("effective_limits")
    return limits if isinstance(limits, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a read-only live recovery-gate observation session.")
    parser.add_argument("--symbols", default="QQQ,NVDA,MSFT")
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    parser.add_argument("--iterations", type=int, default=90)
    args = parser.parse_args()

    try:
        symbols = parse_symbols(args.symbols, "QQQ")
    except ValueError as exc:
        print(json.dumps({"status": "LIVE-RECOVERY-OBSERVER-NO-GO", "reason": str(exc)}))
        return 1
    if args.interval_seconds < 5:
        print(json.dumps({"status": "LIVE-RECOVERY-OBSERVER-NO-GO", "reason": "interval_seconds_must_be_at_least_5"}))
        return 1
    if args.iterations <= 0 or args.iterations > 500:
        print(json.dumps({"status": "LIVE-RECOVERY-OBSERVER-NO-GO", "reason": "iterations_must_be_between_1_and_500"}))
        return 1

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "LIVE-RECOVERY-OBSERVER-NO-GO", "reason": "api_key_missing"}))
        return 1

    try:
        readiness = request_json(api_base, api_key, "/broker/live/readiness")
        limits = effective_limits_from_readiness(readiness)
        print(
            json.dumps(
                {
                    "status": "LIVE-RECOVERY-GATE-LIMITS",
                    "readiness_status": readiness.get("status"),
                    "authorization_status": (
                        readiness.get("authorization", {}).get("status")
                        if isinstance(readiness.get("authorization"), dict)
                        else None
                    ),
                    "effective_limits": limits,
                }
            )
        )
        for cycle in range(1, args.iterations + 1):
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
                gate = recovery_gate_decision(event, limits)
                print(
                    json.dumps(
                        {
                            "status": "LIVE-RECOVERY-OBSERVATION",
                            "cycle": cycle,
                            "symbol": symbol,
                            "watch_status": event.get("watch_status"),
                            "recovery_gate": gate,
                            "event": event,
                        }
                    )
                )
            if cycle < args.iterations:
                time.sleep(args.interval_seconds)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        print(json.dumps({"status": "LIVE-RECOVERY-OBSERVER-STOPPED", "reason": f"http_error:{exc.code}:{body}"}))
        return 1
    except (urllib.error.URLError, RuntimeError) as exc:
        print(json.dumps({"status": "LIVE-RECOVERY-OBSERVER-STOPPED", "reason": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
