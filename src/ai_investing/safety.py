from __future__ import annotations

from dataclasses import dataclass

from .config import SystemConfig
from .models import MarketSnapshot, OrderProposal, PortfolioState


@dataclass
class SafetyDecision:
    approved: bool
    reason: str


class SafetyEngine:
    def __init__(self, config: SystemConfig):
        self.config = config

    def review_market(self, market: MarketSnapshot) -> SafetyDecision:
        if market.price <= 0:
            return SafetyDecision(False, "invalid_price")
        if market.spread_bps > self.config.risk.max_spread_bps:
            return SafetyDecision(False, "spread_too_wide")
        if market.volume_24h < self.config.risk.min_volume_24h:
            return SafetyDecision(False, "insufficient_liquidity")
        if market.volatility_30d > self.config.risk.max_volatility_30d:
            return SafetyDecision(False, "volatility_too_high")
        return SafetyDecision(True, "ok")

    def review_order(
        self,
        order: OrderProposal,
        portfolio: PortfolioState,
        gross_exposure_notional: float,
    ) -> SafetyDecision:
        if self.config.policy.kill_switch:
            return SafetyDecision(False, "kill_switch_active")
        if portfolio.consecutive_losses >= self.config.risk.cooldown_after_losses:
            return SafetyDecision(False, "cooldown_active")

        drawdown = max(0.0, (portfolio.peak_equity - portfolio.equity) / max(portfolio.peak_equity, 1e-9))
        if drawdown > self.config.risk.max_drawdown_pct:
            return SafetyDecision(False, "drawdown_limit_breached")

        if abs(portfolio.daily_pnl) / max(portfolio.equity, 1e-9) > self.config.risk.max_daily_loss_pct and portfolio.daily_pnl < 0:
            return SafetyDecision(False, "daily_loss_limit_breached")

        order_notional = order.quantity * order.limit_price
        if order_notional > self.config.risk.max_order_notional:
            return SafetyDecision(False, "order_notional_too_large")

        symbol_quantity = portfolio.positions.get(order.symbol, 0.0)
        if order.side.value == "SELL" and not self.config.risk.allow_short_sales:
            if symbol_quantity <= 0:
                return SafetyDecision(False, "short_sale_disabled")
            if order.quantity > symbol_quantity:
                return SafetyDecision(False, "sell_quantity_exceeds_position")

        symbol_position = abs(symbol_quantity) * order.limit_price
        if order.side.value == "SELL":
            resulting_symbol_exposure = max(0.0, symbol_position - order_notional)
            resulting_gross_exposure = max(0.0, gross_exposure_notional - order_notional)
        else:
            resulting_symbol_exposure = symbol_position + order_notional
            resulting_gross_exposure = gross_exposure_notional + order_notional

        if resulting_symbol_exposure > portfolio.equity * self.config.risk.max_symbol_exposure_pct:
            return SafetyDecision(False, "symbol_exposure_limit_breached")

        if resulting_gross_exposure > portfolio.equity * self.config.risk.max_gross_exposure_pct:
            return SafetyDecision(False, "gross_exposure_limit_breached")

        return SafetyDecision(True, "ok")

    def net_edge_check(self, expected_edge_bps: float) -> SafetyDecision:
        costs = self.config.costs.fee_bps + self.config.costs.slippage_bps
        net_edge = expected_edge_bps - costs
        if net_edge < self.config.costs.min_net_edge_bps:
            return SafetyDecision(False, "insufficient_net_edge_after_costs")
        return SafetyDecision(True, "ok")
