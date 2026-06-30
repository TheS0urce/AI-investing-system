from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from paper_ops_snapshot import ROOT, fetch_json, load_dotenv
from run_scheduled_market_open_watch import (
    append_log,
    extract_status_lines,
    load_state,
    post_json,
    save_state,
    schedule_decision,
    session_completion_reason,
)


DEFAULT_STATE_PATH = ROOT / "state" / "live_watch_agent.json"
DEFAULT_LOG_PATH = ROOT / "logs" / "live_watch_agent.log"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded live watch once per U.S. session.")
    parser.add_argument("--symbols", default="QQQ,NVDA,MSFT")
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    parser.add_argument("--iterations", type=int, default=90)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--run-after-hour", type=int, default=9)
    parser.add_argument("--run-after-minute", type=int, default=45)
    parser.add_argument("--retry-until-hour", type=int, default=11)
    parser.add_argument("--retry-until-minute", type=int, default=30)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        payload = {"status": "LIVE-NO-GO", "reason": "api_key_missing"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 1

    try:
        exits = post_json(api_base, "/broker/live/protective_exits/check", api_key)
        payload = {"status": "LIVE-PROTECTIVE-EXIT-CHECK", "result": exits}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        authorization = fetch_json(api_base, "/broker/live/authorization", api_key)
        clock_payload = fetch_json(api_base, "/broker/live/clock", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        payload = {"status": "LIVE-NO-GO", "reason": f"http_error:{exc.code}:{body}"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 1
    except urllib.error.URLError as exc:
        payload = {"status": "LIVE-NO-GO", "reason": f"network_error:{exc.reason}"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 1

    if authorization.get("status") != "ACTIVE":
        payload = {"status": "LIVE-WATCH-DISARMED", "reason": "authorization_not_active"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 0

    clock = clock_payload.get("clock") if isinstance(clock_payload.get("clock"), dict) else {}
    state = load_state(args.state_path)
    decision = schedule_decision(
        clock,
        state,
        run_after_hour=args.run_after_hour,
        run_after_minute=args.run_after_minute,
    )
    payload = {"status": "LIVE-SCHEDULE-CHECK", "decision": asdict(decision), "clock": clock}
    append_log(args.log_path, payload)
    print(json.dumps(payload))
    if not decision.should_run:
        return 0

    command = [
        str(ROOT / ".venv" / "bin" / "python"),
        str(ROOT / "scripts" / "run_live_watch.py"),
        "--symbols",
        args.symbols,
        "--feed",
        args.feed,
        "--interval-seconds",
        str(args.interval_seconds),
        "--iterations",
        str(args.iterations),
        "--max-submits",
        "2",
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    submit_events = extract_status_lines(result.stdout, {"LIVE-SUBMIT-OK"})
    proposal_events = [
        event
        for event in extract_status_lines(result.stdout, {"LIVE-WATCH-TICK-OK"})
        if isinstance(event.get("event"), dict)
        and isinstance(event["event"].get("order_proposal"), dict)
    ]
    payload = {
        "status": "LIVE-WATCH-COMPLETED" if result.returncode == 0 else "LIVE-WATCH-FAILED",
        "session_date": decision.session_date,
        "returncode": result.returncode,
        "proposal_count": len(proposal_events),
        "submit_count": len(submit_events),
        "submit_events": submit_events,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    append_log(args.log_path, payload)
    print(json.dumps(payload))
    if result.returncode != 0:
        return result.returncode

    completion_reason = session_completion_reason(
        preauthorized_submit=True,
        proposal_count=len(proposal_events),
        preauthorized_submit_event_count=len(submit_events),
        clock=clock,
        retry_until_hour=args.retry_until_hour,
        retry_until_minute=args.retry_until_minute,
    )
    if completion_reason is None:
        state["last_attempt_session_date"] = decision.session_date
        state["last_attempt_at"] = datetime.now().astimezone().isoformat()
        state["last_attempt_reason"] = "no_live_proposal_before_retry_cutoff"
        state["last_command"] = "run_live_watch"
        save_state(args.state_path, state)
        payload = {
            "status": "LIVE-WATCH-RETRY-ARMED",
            "session_date": decision.session_date,
            "reason": "no_live_proposal_before_retry_cutoff",
        }
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 0

    state["last_completed_session_date"] = decision.session_date
    state["last_completed_at"] = datetime.now().astimezone().isoformat()
    state["last_completed_reason"] = completion_reason
    state["last_command"] = "run_live_watch"
    state["proposal_count"] = len(proposal_events)
    state["submit_count"] = len(submit_events)
    save_state(args.state_path, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
