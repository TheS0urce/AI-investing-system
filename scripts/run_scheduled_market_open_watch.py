from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.paper_ops_snapshot import ROOT, fetch_json, load_dotenv
except ModuleNotFoundError:
    from paper_ops_snapshot import ROOT, fetch_json, load_dotenv


DEFAULT_STATE_PATH = ROOT / "state" / "market_open_watch_agent.json"
DEFAULT_LOG_PATH = ROOT / "logs" / "market_open_watch_agent.log"


@dataclass(frozen=True)
class ScheduleDecision:
    should_run: bool
    reason: str
    session_date: str | None


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def parse_clock_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def schedule_decision(
    clock: dict[str, Any],
    state: dict[str, Any],
    *,
    run_after_hour: int = 9,
    run_after_minute: int = 45,
) -> ScheduleDecision:
    if not bool(clock.get("is_open", False)):
        return ScheduleDecision(False, "market_closed", None)
    timestamp = parse_clock_timestamp(clock.get("timestamp"))
    if timestamp is None:
        return ScheduleDecision(False, "invalid_clock_timestamp", None)

    session_date = timestamp.date().isoformat()
    if state.get("last_completed_session_date") == session_date:
        return ScheduleDecision(False, "session_already_completed", session_date)
    if (timestamp.hour, timestamp.minute) < (run_after_hour, run_after_minute):
        return ScheduleDecision(False, "waiting_for_opening_liquidity_window", session_date)
    return ScheduleDecision(True, "market_open_window_ready", session_date)


def append_log(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


def run_watch_command(args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    command = [
        str(ROOT / ".venv" / "bin" / "python"),
        str(ROOT / "scripts" / "run_market_open_paper_watch.py"),
        "--symbols",
        args.symbols,
        "--feed",
        args.feed,
        "--interval-seconds",
        str(args.interval_seconds),
        "--iterations",
        str(args.iterations),
        "--simulated-equity",
        str(args.simulated_equity),
    ]
    if args.preauthorized_submit:
        command.extend(
            [
                "--preauthorized-submit",
                "--max-preauthorized-submits",
                str(args.max_preauthorized_submits),
            ]
        )
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)


def extract_status_lines(output: str, statuses: set[str]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for line in output.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("status") in statuses:
            matches.append(payload)
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the focused market-open paper watch once per open session.")
    parser.add_argument("--symbols", default="QQQ,NVDA,MSFT")
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    parser.add_argument("--iterations", type=int, default=90)
    parser.add_argument("--simulated-equity", type=float, default=100.0)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--run-after-hour", type=int, default=9)
    parser.add_argument("--run-after-minute", type=int, default=45)
    parser.add_argument("--preauthorized-submit", action="store_true")
    parser.add_argument("--max-preauthorized-submits", type=int, default=2)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_base = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        payload = {"status": "NO-GO", "reason": "api_key_missing"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 1

    try:
        clock_payload = fetch_json(api_base, "/broker/paper/clock", api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")[:500]
        payload = {"status": "NO-GO", "reason": f"http_error:{exc.code}:{body}"}
        append_log(args.log_path, payload)
        print(json.dumps(payload))
        return 1
    except urllib.error.URLError as exc:
        payload = {"status": "NO-GO", "reason": f"network_error:{exc.reason}"}
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
    payload = {
        "status": "SCHEDULE-CHECK",
        "decision": asdict(decision),
        "clock": clock,
    }
    append_log(args.log_path, payload)
    print(json.dumps(payload))
    if not decision.should_run:
        return 0

    result = run_watch_command(args)
    preauthorized_events = extract_status_lines(
        result.stdout,
        {
            "PREAUTHORIZED-SUBMIT-OK",
            "PREAUTHORIZED-SUBMIT-BLOCKED",
            "PREAUTHORIZED-SUBMIT-SKIPPED",
        },
    )
    proposal_events = [
        item
        for item in extract_status_lines(result.stdout, {"WATCH-TICK-OK", "WATCHLIST-TICK-OK"})
        if isinstance(item.get("event"), dict) and isinstance(item["event"].get("order_proposal"), dict)
    ]
    run_payload = {
        "status": "WATCH-COMPLETED" if result.returncode == 0 else "WATCH-FAILED",
        "session_date": decision.session_date,
        "returncode": result.returncode,
        "proposal_count": len(proposal_events),
        "preauthorized_submit_event_count": len(preauthorized_events),
        "preauthorized_submit_events": preauthorized_events,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    append_log(args.log_path, run_payload)
    print(json.dumps(run_payload))
    if result.returncode != 0:
        return result.returncode

    state["last_completed_session_date"] = decision.session_date
    state["last_completed_at"] = datetime.now().astimezone().isoformat()
    state["last_command"] = "run_market_open_paper_watch"
    save_state(args.state_path, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
