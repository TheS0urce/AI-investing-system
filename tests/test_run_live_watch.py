import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

WATCH_SPEC = importlib.util.spec_from_file_location(
    "run_live_watch",
    SCRIPTS_DIR / "run_live_watch.py",
)
live_watch = importlib.util.module_from_spec(WATCH_SPEC)
assert WATCH_SPEC.loader is not None
WATCH_SPEC.loader.exec_module(live_watch)

SCHEDULED_SPEC = importlib.util.spec_from_file_location(
    "run_scheduled_live_watch",
    SCRIPTS_DIR / "run_scheduled_live_watch.py",
)
scheduled_live = importlib.util.module_from_spec(SCHEDULED_SPEC)
assert SCHEDULED_SPEC.loader is not None
SCHEDULED_SPEC.loader.exec_module(scheduled_live)

RECOVERY_OBSERVER_SPEC = importlib.util.spec_from_file_location(
    "run_live_recovery_observer",
    SCRIPTS_DIR / "run_live_recovery_observer.py",
)
recovery_observer = importlib.util.module_from_spec(RECOVERY_OBSERVER_SPEC)
assert RECOVERY_OBSERVER_SPEC.loader is not None
RECOVERY_OBSERVER_SPEC.loader.exec_module(recovery_observer)


def test_proposal_request_requires_market_and_proposal():
    assert live_watch.proposal_request({}) is None
    assert live_watch.proposal_request({"order_proposal": {}}) is None


def test_proposal_request_builds_bounded_submit_payload():
    payload = live_watch.proposal_request(
        {
            "order_proposal": {
                "symbol": "QQQ",
                "side": "BUY",
                "quantity": 0.008,
                "limit_price": 700.0,
                "expected_edge_bps": 10.0,
                "reason": "momentum",
            },
            "market": {"spread_bps": 5.0},
        }
    )

    assert payload == {
        "symbol": "QQQ",
        "side": "BUY",
        "quantity": 0.008,
        "limit_price": 700.0,
        "expected_edge_bps": 10.0,
        "reason": "momentum",
        "spread_bps": 5.0,
    }


def test_controlled_submit_block_reason_recognizes_session_limit():
    body = '{"detail":{"reason":"session_entry_limit_reached"}}'

    assert live_watch.controlled_submit_block_reason(body) == "session_entry_limit_reached"


def test_controlled_submit_block_reason_ignores_unexpected_payloads():
    assert live_watch.controlled_submit_block_reason("not-json") is None
    assert live_watch.controlled_submit_block_reason('{"detail":{"reason":"broker_down"}}') is None


def test_recovery_gate_decision_blocks_weak_edge():
    event = {
        "order_proposal": {
            "symbol": "NVDA",
            "expected_edge_bps": 12.0,
        },
        "market": {"spread_bps": 5.0},
    }
    limits = {"minimum_expected_edge_bps": 13.5, "max_spread_bps": 12.0}

    decision = recovery_observer.recovery_gate_decision(event, limits)

    assert decision["status"] == "BLOCK"
    assert decision["reason"] == "insufficient_expected_edge"


def test_recovery_gate_decision_passes_strong_clean_proposal():
    event = {
        "order_proposal": {
            "symbol": "QQQ",
            "expected_edge_bps": 14.0,
        },
        "market": {"spread_bps": 3.0},
    }
    limits = {"minimum_expected_edge_bps": 13.5, "max_spread_bps": 12.0}

    decision = recovery_observer.recovery_gate_decision(event, limits)

    assert decision["status"] == "PASS"
    assert decision["reason"] == "recovery_gate_pass"


def test_scheduled_live_watch_reuses_retry_aware_session_logic():
    reason = scheduled_live.session_completion_reason(
        preauthorized_submit=True,
        proposal_count=0,
        preauthorized_submit_event_count=0,
        clock={"timestamp": "2026-06-30T10:00:00-04:00"},
        retry_until_hour=11,
        retry_until_minute=30,
    )

    assert reason is None
