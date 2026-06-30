from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import OrderProposal, Side


APPROVED_SYMBOLS = ("SPY", "QQQ", "AAPL", "MSFT", "NVDA")
PAPER_AUTHORIZATION_CONFIRMATION = "AUTHORIZE_BOUNDED_PAPER"
PAPER_REVOCATION_CONFIRMATION = "REVOKE_BOUNDED_PAPER"
LIVE_AUTHORIZATION_CONFIRMATION = "AUTHORIZE_BOUNDED_LIVE"
LIVE_REVOCATION_CONFIRMATION = "REVOKE_BOUNDED_LIVE"


@dataclass(frozen=True)
class PreauthorizationPolicy:
    paper_only: bool = True
    long_only: bool = True
    allowed_symbols: tuple[str, ...] = APPROVED_SYMBOLS
    lease_hours: int = 72
    max_order_notional_usd: float = 4.0
    max_entries_per_session: int = 2
    max_gross_exposure_usd: float = 8.0
    max_daily_loss_usd: float = 2.0
    max_order_capital_pct: float = 0.04
    max_gross_exposure_capital_pct: float = 0.08
    max_daily_loss_capital_pct: float = 0.02
    minimum_order_notional_usd: float = 1.0
    minimum_expected_edge_bps: float = 9.0
    max_spread_bps: float = 30.0
    stop_loss_pct: float = 0.015
    take_profit_pct: float = 0.03
    max_holding_minutes: int = 360
    progression_trade_window: int = 20
    progression_step_pct: float = 0.10
    max_progression_steps: int = 3
    scale_capital_percentages: bool = False
    progression_min_win_rate: float = 0.55
    progression_max_drawdown_pct: float = 0.03
    regression_win_rate: float = 0.45
    pause_consecutive_losses: int = 3
    pause_operational_errors: int = 1


@dataclass(frozen=True)
class PerformanceSnapshot:
    closed_trades: int = 0
    winning_trades: int = 0
    realized_pnl_usd: float = 0.0
    peak_equity_usd: float = 100.0
    current_equity_usd: float = 100.0
    consecutive_losses: int = 0
    operational_errors: int = 0

    @property
    def win_rate(self) -> float:
        return self.winning_trades / self.closed_trades if self.closed_trades else 0.0

    @property
    def drawdown_pct(self) -> float:
        peak = max(self.peak_equity_usd, 1e-9)
        return max(0.0, (self.peak_equity_usd - self.current_equity_usd) / peak)


@dataclass(frozen=True)
class EffectiveLimits:
    risk_level: int
    status: str
    reason: str
    available_capital_usd: float
    max_order_notional_usd: float
    max_entries_per_session: int
    max_gross_exposure_usd: float
    max_daily_loss_usd: float


@dataclass
class PreauthorizationState:
    active: bool = False
    activated_at: str | None = None
    expires_at: str | None = None
    revoked_at: str | None = None
    paper_only: bool = True
    session_date: str | None = None
    entries_this_session: int = 0
    gross_exposure_usd: float = 0.0
    daily_realized_pnl_usd: float = 0.0
    closed_trades: int = 0
    winning_trades: int = 0
    realized_pnl_usd: float = 0.0
    peak_equity_usd: float = 100.0
    current_equity_usd: float = 100.0
    consecutive_losses: int = 0
    operational_errors: int = 0
    audit: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class AuthorizationContext:
    broker_mode: str
    live_enabled: bool
    market_is_open: bool
    session_date: str
    gross_exposure_usd: float
    daily_realized_pnl_usd: float
    open_order_symbols: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuthorizationDecision:
    approved: bool
    reason: str
    effective_limits: EffectiveLimits


@dataclass(frozen=True)
class ProtectiveExitPlan:
    symbol: str
    quantity: float
    entry_price: float
    stop_price: float
    take_profit_price: float
    max_holding_minutes: int
    time_in_force: str = "day"
    regular_hours_only: bool = True


def performance_from_state(state: PreauthorizationState) -> PerformanceSnapshot:
    return PerformanceSnapshot(
        closed_trades=state.closed_trades,
        winning_trades=state.winning_trades,
        realized_pnl_usd=state.realized_pnl_usd,
        peak_equity_usd=state.peak_equity_usd,
        current_equity_usd=state.current_equity_usd,
        consecutive_losses=state.consecutive_losses,
        operational_errors=state.operational_errors,
    )


def effective_limits(
    performance: PerformanceSnapshot,
    policy: PreauthorizationPolicy | None = None,
    available_capital_usd: float | None = None,
) -> EffectiveLimits:
    policy = policy or PreauthorizationPolicy()
    capital = performance.current_equity_usd if available_capital_usd is None else available_capital_usd
    if capital <= 0:
        return EffectiveLimits(
            0,
            "PAUSED",
            "available_capital_invalid",
            max(0.0, capital),
            0.0,
            0,
            0.0,
            0.0,
        )

    capital_loss_cap = capital * policy.max_daily_loss_capital_pct

    def limits_for(
        *,
        risk_level: int,
        status: str,
        reason: str,
        scale: float,
        entries: int,
    ) -> EffectiveLimits:
        capital_scale = scale if policy.scale_capital_percentages else 1.0
        capital_order_cap = capital * policy.max_order_capital_pct * capital_scale
        capital_exposure_cap = (
            capital * policy.max_gross_exposure_capital_pct * capital_scale
        )
        return EffectiveLimits(
            risk_level=risk_level,
            status=status,
            reason=reason,
            available_capital_usd=round(capital, 2),
            max_order_notional_usd=round(
                min(policy.max_order_notional_usd * scale, capital_order_cap),
                2,
            ),
            max_entries_per_session=entries,
            max_gross_exposure_usd=round(
                min(policy.max_gross_exposure_usd * scale, capital_exposure_cap),
                2,
            ),
            # Capital declines tighten this ceiling; growth never expands it above
            # the manually governed dollar cap.
            max_daily_loss_usd=round(min(policy.max_daily_loss_usd, capital_loss_cap), 2),
        )

    if performance.operational_errors >= policy.pause_operational_errors:
        return limits_for(
            risk_level=0,
            status="PAUSED",
            reason="operational_error_pause",
            scale=1.0,
            entries=policy.max_entries_per_session,
        )
    if performance.consecutive_losses >= policy.pause_consecutive_losses:
        return limits_for(
            risk_level=0,
            status="PAUSED",
            reason="consecutive_loss_pause",
            scale=1.0,
            entries=policy.max_entries_per_session,
        )

    completed_windows = performance.closed_trades // policy.progression_trade_window
    qualified = (
        completed_windows > 0
        and performance.realized_pnl_usd > 0
        and performance.win_rate >= policy.progression_min_win_rate
        and performance.drawdown_pct <= policy.progression_max_drawdown_pct
    )
    risk_level = min(completed_windows, policy.max_progression_steps) if qualified else 0

    regression = (
        performance.closed_trades >= policy.progression_trade_window
        and (
            performance.realized_pnl_usd < 0
            or performance.win_rate < policy.regression_win_rate
            or performance.drawdown_pct > policy.progression_max_drawdown_pct
        )
    )
    scale = 0.90 if regression else 1.0 + risk_level * policy.progression_step_pct
    status = "TIGHTENED" if regression else "ACTIVE"
    reason = "performance_regression" if regression else "within_governed_envelope"

    return limits_for(
        risk_level=risk_level,
        status=status,
        reason=reason,
        scale=scale,
        entries=max(
            1,
            policy.max_entries_per_session + risk_level - (1 if regression else 0),
        ),
    )


def authorization_is_active(
    state: PreauthorizationState,
    now: datetime | None = None,
    *,
    required_paper_only: bool = True,
) -> bool:
    if (
        not state.active
        or not state.expires_at
        or state.paper_only != required_paper_only
    ):
        return False
    now = now or datetime.now(timezone.utc)
    try:
        expires_at = datetime.fromisoformat(state.expires_at)
    except ValueError:
        return False
    return now < expires_at


def authorize_entry(
    order: OrderProposal,
    *,
    spread_bps: float,
    state: PreauthorizationState,
    context: AuthorizationContext,
    policy: PreauthorizationPolicy | None = None,
    now: datetime | None = None,
) -> AuthorizationDecision:
    policy = policy or PreauthorizationPolicy()
    limits = effective_limits(performance_from_state(state), policy)
    if limits.status == "PAUSED":
        return AuthorizationDecision(False, limits.reason, limits)
    if not authorization_is_active(
        state,
        now,
        required_paper_only=policy.paper_only,
    ):
        return AuthorizationDecision(False, "authorization_inactive_or_expired", limits)
    if policy.paper_only:
        if context.broker_mode != "paper" or context.live_enabled:
            return AuthorizationDecision(False, "paper_only_guard_failed", limits)
    elif context.broker_mode != "live" or not context.live_enabled:
        return AuthorizationDecision(False, "live_only_guard_failed", limits)
    if not context.market_is_open:
        return AuthorizationDecision(False, "regular_market_hours_required", limits)
    if order.symbol.upper() not in policy.allowed_symbols:
        return AuthorizationDecision(False, "symbol_not_preauthorized", limits)
    if policy.long_only and order.side != Side.BUY:
        return AuthorizationDecision(False, "long_only_entry_required", limits)
    if spread_bps > policy.max_spread_bps:
        return AuthorizationDecision(False, "spread_too_wide", limits)
    if order.expected_edge_bps < policy.minimum_expected_edge_bps:
        return AuthorizationDecision(False, "insufficient_expected_edge", limits)

    order_notional = order.quantity * order.limit_price
    if order_notional < policy.minimum_order_notional_usd:
        return AuthorizationDecision(False, "order_below_fractional_minimum", limits)
    if order_notional > limits.max_order_notional_usd:
        return AuthorizationDecision(False, "preauthorized_order_limit_exceeded", limits)

    entries = state.entries_this_session if state.session_date == context.session_date else 0
    if entries >= limits.max_entries_per_session:
        return AuthorizationDecision(False, "session_entry_limit_reached", limits)
    if context.gross_exposure_usd + order_notional > limits.max_gross_exposure_usd:
        return AuthorizationDecision(False, "preauthorized_exposure_limit_exceeded", limits)
    daily_realized_pnl = (
        context.daily_realized_pnl_usd
        if state.session_date == context.session_date
        else 0.0
    )
    if daily_realized_pnl <= -limits.max_daily_loss_usd:
        return AuthorizationDecision(False, "preauthorized_daily_loss_limit_reached", limits)
    if order.symbol.upper() in context.open_order_symbols:
        return AuthorizationDecision(False, "duplicate_symbol_order_open", limits)
    reason = "preauthorized_paper_entry" if policy.paper_only else "preauthorized_live_entry"
    return AuthorizationDecision(True, reason, limits)


def protective_exit_plan(
    *,
    symbol: str,
    quantity: float,
    entry_price: float,
    policy: PreauthorizationPolicy | None = None,
) -> ProtectiveExitPlan:
    policy = policy or PreauthorizationPolicy()
    if quantity <= 0 or entry_price <= 0:
        raise ValueError("positive_position_required")
    return ProtectiveExitPlan(
        symbol=symbol.upper(),
        quantity=quantity,
        entry_price=entry_price,
        stop_price=round(entry_price * (1.0 - policy.stop_loss_pct), 2),
        take_profit_price=round(entry_price * (1.0 + policy.take_profit_pct), 2),
        max_holding_minutes=policy.max_holding_minutes,
    )


class PreauthorizationStore:
    def __init__(
        self,
        path: Path,
        *,
        paper_only: bool = True,
        authorization_confirmation: str = PAPER_AUTHORIZATION_CONFIRMATION,
        revocation_confirmation: str = PAPER_REVOCATION_CONFIRMATION,
        event_prefix: str = "paper",
    ):
        self.path = path
        self.paper_only = paper_only
        self.authorization_confirmation = authorization_confirmation
        self.revocation_confirmation = revocation_confirmation
        self.event_prefix = event_prefix

    def load(self) -> PreauthorizationState:
        if not self.path.exists():
            return PreauthorizationState(paper_only=self.paper_only)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return PreauthorizationState(
                paper_only=self.paper_only,
                operational_errors=1,
                audit=[{"event": "state_load_failed", "at": datetime.now(timezone.utc).isoformat()}],
            )
        if not isinstance(payload, dict):
            return PreauthorizationState(
                paper_only=self.paper_only,
                operational_errors=1,
            )
        fields = PreauthorizationState.__dataclass_fields__
        values = {key: value for key, value in payload.items() if key in fields}
        values.setdefault("paper_only", self.paper_only)
        return PreauthorizationState(**values)

    def save(self, state: PreauthorizationState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    def activate(
        self,
        *,
        confirmation: str,
        now: datetime | None = None,
        policy: PreauthorizationPolicy | None = None,
        available_capital_usd: float | None = None,
    ) -> PreauthorizationState:
        if confirmation != self.authorization_confirmation:
            raise ValueError("preauthorization_confirmation_required")
        policy = policy or PreauthorizationPolicy()
        if policy.paper_only != self.paper_only:
            raise ValueError("preauthorization_policy_mode_mismatch")
        if available_capital_usd is not None and available_capital_usd <= 0:
            raise ValueError("available_capital_must_be_positive")
        now = now or datetime.now(timezone.utc)
        state = self.load()
        state.active = True
        state.paper_only = self.paper_only
        state.activated_at = now.isoformat()
        state.expires_at = (now + timedelta(hours=policy.lease_hours)).isoformat()
        state.revoked_at = None
        state.operational_errors = 0
        if available_capital_usd is not None:
            state.current_equity_usd = round(available_capital_usd, 6)
            state.peak_equity_usd = max(state.peak_equity_usd, state.current_equity_usd)
        state.audit.append(
            {
                "event": f"{self.event_prefix}_preauthorization_activated",
                "at": now.isoformat(),
            }
        )
        state.audit = state.audit[-200:]
        self.save(state)
        return state

    def revoke(
        self,
        *,
        confirmation: str,
        now: datetime | None = None,
    ) -> PreauthorizationState:
        if confirmation != self.revocation_confirmation:
            raise ValueError("preauthorization_revocation_confirmation_required")
        now = now or datetime.now(timezone.utc)
        state = self.load()
        state.active = False
        state.revoked_at = now.isoformat()
        state.audit.append(
            {
                "event": f"{self.event_prefix}_preauthorization_revoked",
                "at": now.isoformat(),
            }
        )
        state.audit = state.audit[-200:]
        self.save(state)
        return state

    def record_entry(
        self,
        *,
        session_date: str,
        order_notional_usd: float,
        symbol: str,
        now: datetime | None = None,
    ) -> PreauthorizationState:
        now = now or datetime.now(timezone.utc)
        state = self.load()
        if state.session_date != session_date:
            state.session_date = session_date
            state.entries_this_session = 0
            state.daily_realized_pnl_usd = 0.0
        state.entries_this_session += 1
        state.gross_exposure_usd = round(state.gross_exposure_usd + order_notional_usd, 6)
        state.audit.append(
            {
                "event": f"{self.event_prefix}_entry_recorded",
                "at": now.isoformat(),
                "symbol": symbol.upper(),
                "notional_usd": order_notional_usd,
            }
        )
        state.audit = state.audit[-200:]
        self.save(state)
        return state

    def record_closed_trade(
        self,
        *,
        realized_pnl_usd: float,
        released_exposure_usd: float,
        current_equity_usd: float,
        symbol: str,
        now: datetime | None = None,
    ) -> PreauthorizationState:
        now = now or datetime.now(timezone.utc)
        state = self.load()
        state.closed_trades += 1
        if realized_pnl_usd > 0:
            state.winning_trades += 1
            state.consecutive_losses = 0
        else:
            state.consecutive_losses += 1
        state.realized_pnl_usd = round(state.realized_pnl_usd + realized_pnl_usd, 6)
        state.daily_realized_pnl_usd = round(state.daily_realized_pnl_usd + realized_pnl_usd, 6)
        state.current_equity_usd = current_equity_usd
        state.peak_equity_usd = max(state.peak_equity_usd, current_equity_usd)
        state.gross_exposure_usd = round(max(0.0, state.gross_exposure_usd - released_exposure_usd), 6)
        state.audit.append(
            {
                "event": f"{self.event_prefix}_trade_closed",
                "at": now.isoformat(),
                "symbol": symbol.upper(),
                "realized_pnl_usd": realized_pnl_usd,
            }
        )
        state.audit = state.audit[-200:]
        self.save(state)
        return state

    def record_operational_error(self, reason: str, now: datetime | None = None) -> PreauthorizationState:
        now = now or datetime.now(timezone.utc)
        state = self.load()
        state.operational_errors += 1
        state.active = False
        state.audit.append({"event": "operational_error_pause", "at": now.isoformat(), "reason": reason})
        state.audit = state.audit[-200:]
        self.save(state)
        return state
