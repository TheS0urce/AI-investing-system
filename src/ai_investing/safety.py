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
        if market.price <= 0: return SafetyDecision(False, "invalid_price")
        if market.spread_bps > self.config.risk.max_spread_bps: return SafetyDecision(False, "spread_too_wide")
        if market.volume_24h < self.config.risk.min_volume_24h: return SafetyDecision(False, "insufficient_liquidity")
        if market.volatility_30d > self.config.risk.max_volatility_30d: return SafetyDecision(False, "volatility_too_high")
        return SafetyDecision(True, "ok")

    def review_order(self, order: OrderProposal, portfolio: PortfolioState, gross_exposure_notional: float) -> SafetyDecision:
        if self.config.policy.kill_switch: return SafetyDecision(False, "kill_switch_active")
        if portfolio.consecutive_losses >= self.config.risk.cooldown_after_losses: return SafetyDecision(False, "cooldown_active")
        return SafetyDecision(True, "ok")

    def net_edge_check(self, expected_edge_bps: float) -> SafetyDecision:
        costs = self.config.costs.fee_bps + self.config.costs.slippage_bps
        return SafetyDecision(expected_edge_bps - costs >= self.config.costs.min_net_edge_bps, "ok" if expected_edge_bps - costs >= self.config.costs.min_net_edge_bps else "insufficient_net_edge_after_costs")
