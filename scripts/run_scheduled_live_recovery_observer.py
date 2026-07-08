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
    save_state,
    schedule_decision,
)


DEFAULT_STATE_PATH = ROOT / "state" / "live_recovery_observer_agent.json"
DEFAULT_LOG_PATH = ROOT / "logs" / "live_recovery_observer_agent.log"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one read-only live recovery-gate observation per U.S. session.")
    parser.add_argument("--symbols", default="QQQ,NVDA,MSFT")
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    parser.add_argument("--iterations", type=int, default=90)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--run-after-hour", type=int, default=9)
    parser.add_argument("--run-after-minute", type=int, default=45)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        payload = {"status": "LIVE-RECOVERY-OBSERVER-NO-GO", "reason": "api_key_missing"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 1

    try:
        clock_payload = fetch_json(api_base, "/broker/live/clock", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        payload = {"status": "LIVE-RECOVERY-OBSERVER-NO-GO", "reason": f"http_error:{exc.code}:{body}"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 1
    except urllib.error.URLError as exc:
        payload = {"status": "LIVE-RECOVERY-OBSERVER-NO-GO", "reason": f"network_error:{exc.reason}"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 1

    clock = clock_payload.get("clock") if isinstance(clock_payload.get("clock"), dict) else {}
    state = load_state(args.state_path)
    decision = schedule_decision(
        clock,
        state,
        run_after_hour=args.run_after_hour,
        run_after_minute=args.run_after_minute,
    )
    payload = {"status": "LIVE-RECOVERY-SCHEDULE-CHECK", "decision": asdict(decision), "clock": clock}
    append_log(args.log_path, payload)
    print(json.dumps(payload))
    if not decision.should_run:
        return 0

    command = [
        str(ROOT / ".venv" / "bin" / "python"),
        str(ROOT / "scripts" / "run_live_recovery_observer.py"),
        "--symbols",
        args.symbols,
        "--feed",
        args.feed,
        "--interval-seconds",
        str(args.interval_seconds),
        "--iterations",
        str(args.iterations),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    observations = extract_status_lines(result.stdout, {"LIVE-RECOVERY-OBSERVATION"})
    gate_passes = [
        item
        for item in observations
        if isinstance(item.get("recovery_gate"), dict)
        and item["recovery_gate"].get("status") == "PASS"
    ]
    payload = {
        "status": "LIVE-RECOVERY-OBSERVER-COMPLETED" if result.returncode == 0 else "LIVE-RECOVERY-OBSERVER-FAILED",
        "session_date": decision.session_date,
        "returncode": result.returncode,
        "observation_count": len(observations),
        "gate_pass_count": len(gate_passes),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    append_log(args.log_path, payload)
    print(json.dumps(payload))
    if result.returncode != 0:
        return result.returncode

    state["last_completed_session_date"] = decision.session_date
    state["last_completed_at"] = datetime.now().astimezone().isoformat()
    state["last_completion_reason"] = "read_only_recovery_observation_completed"
    state["last_observation_count"] = len(observations)
    state["last_gate_pass_count"] = len(gate_passes)
    state["last_command"] = "run_live_recovery_observer"
    save_state(args.state_path, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
