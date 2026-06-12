import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location(
    "paper_preauthorization_replay_report",
    SCRIPTS_DIR / "paper_preauthorization_replay_report.py",
)
report_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["paper_preauthorization_replay_report"] = report_module
SPEC.loader.exec_module(report_module)


def event(side: str, *, symbol: str = "QQQ", notional: float = 2.0, edge: float = 12.0, spread: float = 5.0):
    return {
        "at": "2026-06-10T13:45:00+00:00",
        "watch_status": "EVALUATED",
        "market": {"spread_bps": spread},
        "order_proposal": {
            "symbol": symbol,
            "side": side,
            "quantity": notional / 100.0,
            "limit_price": 100.0,
            "expected_edge_bps": edge,
            "reason": "test",
        },
    }


def test_replay_approves_bounded_buy_and_rejects_sell():
    report = report_module.build_preauthorization_replay_report([event("BUY"), event("SELL")])

    assert report["proposal_count"] == 2
    assert report["eligible_count"] == 1
    assert report["eligible_symbols"] == {"QQQ": 1}
    assert report["decision_reasons"] == {
        "long_only_entry_required": 1,
        "preauthorized_paper_entry": 1,
    }
    assert report["paper_orders_submitted"] == 0
    assert report["authorization_activated"] is False


def test_replay_rejects_orders_outside_policy_envelope():
    report = report_module.build_preauthorization_replay_report(
        [
            event("BUY", symbol="TSLA"),
            event("BUY", notional=4.01),
            event("BUY", edge=8.0),
            event("BUY", spread=31.0),
        ]
    )

    assert report["eligible_count"] == 0
    assert report["decision_reasons"] == {
        "insufficient_expected_edge": 1,
        "preauthorized_order_limit_exceeded": 1,
        "spread_too_wide": 1,
        "symbol_not_preauthorized": 1,
    }


def test_markdown_keeps_replay_read_only():
    report = report_module.build_preauthorization_replay_report([event("BUY")])
    markdown = report_module.format_markdown_report(report, "2026-06-13T00:00:00+00:00")

    assert "read-only replay" in markdown
    assert "Authorization activated: `False`" in markdown
    assert "Paper orders submitted: `0`" in markdown
    assert "Fractional bracket verified by broker: `False`" in markdown
