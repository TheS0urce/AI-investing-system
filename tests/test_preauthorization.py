from datetime import datetime, timedelta, timezone

import pytest

from src.ai_investing.models import OrderProposal, Side
from src.ai_investing.preauthorization import (
    AuthorizationContext,
    PAPER_AUTHORIZATION_CONFIRMATION,
    PAPER_REVOCATION_CONFIRMATION,
    PerformanceSnapshot,
    PreauthorizationPolicy,
    PreauthorizationState,
    PreauthorizationStore,
    authorization_is_active,
    authorize_entry,
    effective_limits,
    performance_from_state,
    protective_exit_plan,
)


NOW = datetime(2026, 6, 12, 1, 0, tzinfo=timezone.utc)


def active_state(**overrides) -> PreauthorizationState:
    values = {
        "active": True,
        "activated_at": NOW.isoformat(),
        "expires_at": (NOW + timedelta(hours=72)).isoformat(),
        "paper_only": True,
        "session_date": "2026-06-12",
        "entries_this_session": 0,
        "gross_exposure_usd": 0.0,
        "daily_realized_pnl_usd": 0.0,
    }
    values.update(overrides)
    return PreauthorizationState(**values)


def buy_order(notional: float = 4.0, edge_bps: float = 10.0, symbol: str = "QQQ") -> OrderProposal:
    return OrderProposal(
        symbol=symbol,
        side=Side.BUY,
        quantity=notional / 100.0,
        limit_price=100.0,
        expected_edge_bps=edge_bps,
        reason="test",
    )


def context(**overrides) -> AuthorizationContext:
    values = {
        "broker_mode": "paper",
        "live_enabled": False,
        "market_is_open": True,
        "session_date": "2026-06-12",
        "gross_exposure_usd": 0.0,
        "daily_realized_pnl_usd": 0.0,
        "open_order_symbols": (),
    }
    values.update(overrides)
    return AuthorizationContext(**values)


def test_authorization_active_only_before_expiry():
    state = active_state()

    assert authorization_is_active(state, NOW)
    assert not authorization_is_active(state, NOW + timedelta(hours=73))


def test_base_policy_approves_bounded_paper_buy():
    decision = authorize_entry(
        buy_order(),
        spread_bps=5.0,
        state=active_state(),
        context=context(),
        now=NOW,
    )

    assert decision.approved
    assert decision.reason == "preauthorized_paper_entry"
    assert decision.effective_limits.available_capital_usd == 100.0
    assert decision.effective_limits.max_order_notional_usd == 4.0
    assert decision.effective_limits.max_daily_loss_usd == 2.0


@pytest.mark.parametrize(
    ("order", "ctx", "reason"),
    [
        (buy_order(symbol="TSLA"), context(), "symbol_not_preauthorized"),
        (
            OrderProposal("QQQ", Side.SELL, 0.01, 100.0, 10.0, "test"),
            context(),
            "long_only_entry_required",
        ),
        (buy_order(), context(broker_mode="live"), "paper_only_guard_failed"),
        (buy_order(), context(live_enabled=True), "paper_only_guard_failed"),
        (buy_order(), context(market_is_open=False), "regular_market_hours_required"),
        (buy_order(notional=4.01), context(), "preauthorized_order_limit_exceeded"),
        (buy_order(notional=0.99), context(), "order_below_fractional_minimum"),
        (buy_order(edge_bps=8.99), context(), "insufficient_expected_edge"),
        (buy_order(), context(gross_exposure_usd=5.0), "preauthorized_exposure_limit_exceeded"),
        (buy_order(), context(daily_realized_pnl_usd=-2.0), "preauthorized_daily_loss_limit_reached"),
        (buy_order(), context(open_order_symbols=("QQQ",)), "duplicate_symbol_order_open"),
    ],
)
def test_base_policy_rejects_outside_envelope(order, ctx, reason):
    decision = authorize_entry(
        order,
        spread_bps=5.0,
        state=active_state(),
        context=ctx,
        now=NOW,
    )

    assert not decision.approved
    assert decision.reason == reason


def test_prior_session_daily_loss_does_not_block_new_session():
    decision = authorize_entry(
        buy_order(),
        spread_bps=5.0,
        state=active_state(session_date="2026-06-11", daily_realized_pnl_usd=-2.0),
        context=context(session_date="2026-06-12", daily_realized_pnl_usd=-2.0),
        now=NOW,
    )

    assert decision.approved


def test_session_entry_limit_is_enforced():
    decision = authorize_entry(
        buy_order(),
        spread_bps=5.0,
        state=active_state(entries_this_session=2),
        context=context(),
        now=NOW,
    )

    assert not decision.approved
    assert decision.reason == "session_entry_limit_reached"


def test_expired_authorization_fails_closed():
    decision = authorize_entry(
        buy_order(),
        spread_bps=5.0,
        state=active_state(expires_at=(NOW - timedelta(seconds=1)).isoformat()),
        context=context(),
        now=NOW,
    )

    assert not decision.approved
    assert decision.reason == "authorization_inactive_or_expired"


def test_progression_relaxes_opportunity_limits_but_not_loss_ceiling():
    limits = effective_limits(
        PerformanceSnapshot(
            closed_trades=40,
            winning_trades=24,
            realized_pnl_usd=8.0,
            peak_equity_usd=208.0,
            current_equity_usd=207.0,
        )
    )

    assert limits.risk_level == 2
    assert limits.available_capital_usd == 207.0
    assert limits.max_order_notional_usd == 4.8
    assert limits.max_entries_per_session == 4
    assert limits.max_gross_exposure_usd == 9.6
    assert limits.max_daily_loss_usd == 2.0


def test_performance_regression_tightens_limits():
    limits = effective_limits(
        PerformanceSnapshot(
            closed_trades=20,
            winning_trades=7,
            realized_pnl_usd=-1.0,
            peak_equity_usd=100.0,
            current_equity_usd=96.0,
        )
    )

    assert limits.status == "TIGHTENED"
    assert limits.max_order_notional_usd == 3.6
    assert limits.max_entries_per_session == 1
    assert limits.max_gross_exposure_usd == 7.2
    assert limits.max_daily_loss_usd == 1.92


def test_capital_decline_tightens_all_money_limits_immediately():
    limits = effective_limits(PerformanceSnapshot(current_equity_usd=50.0))

    assert limits.available_capital_usd == 50.0
    assert limits.max_order_notional_usd == 2.0
    assert limits.max_gross_exposure_usd == 4.0
    assert limits.max_daily_loss_usd == 1.0


def test_capital_growth_requires_performance_before_limits_expand():
    unproven = effective_limits(PerformanceSnapshot(current_equity_usd=200.0))
    proven = effective_limits(
        PerformanceSnapshot(
            closed_trades=20,
            winning_trades=12,
            realized_pnl_usd=5.0,
            peak_equity_usd=200.0,
            current_equity_usd=200.0,
        )
    )

    assert unproven.max_order_notional_usd == 4.0
    assert unproven.max_gross_exposure_usd == 8.0
    assert proven.max_order_notional_usd == 4.4
    assert proven.max_gross_exposure_usd == 8.8
    assert proven.max_daily_loss_usd == 2.0


def test_low_capital_can_make_fractional_minimum_unavailable():
    decision = authorize_entry(
        buy_order(notional=1.0),
        spread_bps=5.0,
        state=active_state(current_equity_usd=20.0),
        context=context(),
        now=NOW,
    )

    assert not decision.approved
    assert decision.reason == "preauthorized_order_limit_exceeded"
    assert decision.effective_limits.max_order_notional_usd == 0.8


def test_invalid_capital_pauses_new_entries():
    limits = effective_limits(PerformanceSnapshot(current_equity_usd=0.0))

    assert limits.status == "PAUSED"
    assert limits.reason == "available_capital_invalid"
    assert limits.max_order_notional_usd == 0.0


@pytest.mark.parametrize(
    ("performance", "reason"),
    [
        (PerformanceSnapshot(consecutive_losses=3), "consecutive_loss_pause"),
        (PerformanceSnapshot(operational_errors=1), "operational_error_pause"),
    ],
)
def test_pause_conditions_stop_new_entries(performance, reason):
    limits = effective_limits(performance)
    assert limits.status == "PAUSED"
    assert limits.reason == reason


def test_protective_exit_plan_is_bounded_and_regular_hours_only():
    plan = protective_exit_plan(symbol="qqq", quantity=0.005, entry_price=700.0)

    assert plan.symbol == "QQQ"
    assert plan.stop_price == 689.5
    assert plan.take_profit_price == 721.0
    assert plan.max_holding_minutes == 360
    assert plan.time_in_force == "day"
    assert plan.regular_hours_only


def test_store_activation_expiry_entry_close_and_revocation(tmp_path):
    store = PreauthorizationStore(tmp_path / "paper_preauthorization.json")

    with pytest.raises(ValueError, match="preauthorization_confirmation_required"):
        store.activate(confirmation="NO", now=NOW)

    activated = store.activate(confirmation=PAPER_AUTHORIZATION_CONFIRMATION, now=NOW)
    assert activated.active
    assert activated.paper_only
    assert activated.expires_at == (NOW + timedelta(hours=72)).isoformat()

    entered = store.record_entry(
        session_date="2026-06-12",
        order_notional_usd=4.0,
        symbol="QQQ",
        now=NOW,
    )
    assert entered.entries_this_session == 1
    assert entered.gross_exposure_usd == 4.0

    closed = store.record_closed_trade(
        realized_pnl_usd=0.25,
        released_exposure_usd=4.0,
        current_equity_usd=100.25,
        symbol="QQQ",
        now=NOW,
    )
    assert closed.closed_trades == 1
    assert closed.winning_trades == 1
    assert closed.realized_pnl_usd == 0.25
    assert closed.gross_exposure_usd == 0.0
    limits = effective_limits(performance_from_state(closed))
    assert limits.available_capital_usd == 100.25
    assert limits.max_order_notional_usd == 4.0

    revoked = store.revoke(confirmation=PAPER_REVOCATION_CONFIRMATION, now=NOW)
    assert not revoked.active
    assert revoked.revoked_at == NOW.isoformat()


def test_store_operational_error_revokes_authorization(tmp_path):
    store = PreauthorizationStore(tmp_path / "paper_preauthorization.json")
    store.activate(confirmation=PAPER_AUTHORIZATION_CONFIRMATION, now=NOW)

    state = store.record_operational_error("broker_timeout", now=NOW)

    assert not state.active
    assert state.operational_errors == 1
    assert state.audit[-1]["reason"] == "broker_timeout"


def test_reviewed_activation_clears_operational_error_latch(tmp_path):
    store = PreauthorizationStore(tmp_path / "paper_preauthorization.json")
    store.record_operational_error("broker_timeout", now=NOW)

    state = store.activate(
        confirmation=PAPER_AUTHORIZATION_CONFIRMATION,
        now=NOW + timedelta(minutes=1),
    )

    assert state.active
    assert state.operational_errors == 0


def test_policy_starts_with_requested_high_aversion_limits():
    policy = PreauthorizationPolicy()

    assert policy.max_order_notional_usd == 4.0
    assert policy.max_entries_per_session == 2
    assert policy.max_gross_exposure_usd == 8.0
    assert policy.max_daily_loss_usd == 2.0
    assert policy.max_order_capital_pct == 0.04
    assert policy.max_gross_exposure_capital_pct == 0.08
    assert policy.max_daily_loss_capital_pct == 0.02
    assert policy.stop_loss_pct == 0.015
    assert policy.take_profit_pct == 0.03
