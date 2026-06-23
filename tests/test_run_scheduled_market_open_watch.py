import importlib.util
import argparse
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location(
    "run_scheduled_market_open_watch",
    SCRIPTS_DIR / "run_scheduled_market_open_watch.py",
)
scheduled = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["run_scheduled_market_open_watch"] = scheduled
SPEC.loader.exec_module(scheduled)


def clock(timestamp, is_open=True):
    return {
        "is_open": is_open,
        "timestamp": timestamp,
        "next_open": "2026-06-16T09:30:00-04:00",
        "next_close": "2026-06-16T16:00:00-04:00",
    }


def test_schedule_decision_waits_when_market_closed():
    decision = scheduled.schedule_decision(clock("2026-06-16T08:30:00-04:00", is_open=False), {})

    assert decision.should_run is False
    assert decision.reason == "market_closed"


def test_schedule_decision_waits_until_opening_liquidity_window():
    decision = scheduled.schedule_decision(clock("2026-06-16T09:44:59-04:00"), {})

    assert decision.should_run is False
    assert decision.reason == "waiting_for_opening_liquidity_window"
    assert decision.session_date == "2026-06-16"


def test_schedule_decision_runs_once_after_opening_window():
    decision = scheduled.schedule_decision(clock("2026-06-16T09:45:00-04:00"), {})

    assert decision.should_run is True
    assert decision.reason == "market_open_window_ready"
    assert decision.session_date == "2026-06-16"


def test_schedule_decision_skips_completed_session():
    decision = scheduled.schedule_decision(
        clock("2026-06-16T10:00:00-04:00"),
        {"last_completed_session_date": "2026-06-16"},
    )

    assert decision.should_run is False
    assert decision.reason == "session_already_completed"


def test_schedule_decision_rejects_invalid_timestamp():
    decision = scheduled.schedule_decision({"is_open": True, "timestamp": "bad"}, {})

    assert decision.should_run is False
    assert decision.reason == "invalid_clock_timestamp"


def test_run_watch_command_includes_preauthorized_submit_flags(monkeypatch):
    captured = {}

    def fake_run(command, cwd, text, capture_output, check):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["text"] = text
        captured["capture_output"] = capture_output
        captured["check"] = check
        return "completed"

    monkeypatch.setattr(scheduled.subprocess, "run", fake_run)

    result = scheduled.run_watch_command(
        argparse.Namespace(
            symbols="QQQ,NVDA",
            feed="iex",
            interval_seconds=10,
            iterations=30,
            simulated_equity=100,
            preauthorized_submit=True,
            max_preauthorized_submits=2,
        )
    )

    assert result == "completed"
    assert "--preauthorized-submit" in captured["command"]
    assert captured["command"][-2:] == ["--max-preauthorized-submits", "2"]


def test_extract_status_lines_returns_matching_json_payloads():
    output = "\n".join(
        [
            '{"status":"WATCHLIST-TICK-OK","event":{"order_proposal":{"symbol":"NVDA"}}}',
            "not-json",
            '{"status":"PREAUTHORIZED-SUBMIT-BLOCKED","reason":"expired"}',
            '{"status":"PREFLIGHT-CHECK"}',
        ]
    )

    matches = scheduled.extract_status_lines(
        output,
        {"WATCHLIST-TICK-OK", "PREAUTHORIZED-SUBMIT-BLOCKED"},
    )

    assert [item["status"] for item in matches] == [
        "WATCHLIST-TICK-OK",
        "PREAUTHORIZED-SUBMIT-BLOCKED",
    ]
