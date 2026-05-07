from __future__ import annotations

from datetime import datetime

from .config import SystemConfig
from .execution import ExecutionPlanner
from .models import AuditEvent, MarketSnapshot, OrderProposal, PortfolioState
from .safety import SafetyEngine
from .strategy import Strategy


class InvestingSystem:
    def __init__(self, config: SystemConfig, strategy: Strategy):
        self.config = config
        self.strategy = strategy
        self.safety = SafetyEngine(config)
        self.execution = ExecutionPlanner()
        self.audit_log: list[AuditEvent] = []

    def _audit(self, event: str, severity: str, details: str) -> None:
        self.audit_log.append(AuditEvent(datetime.utcnow(), event, severity, details))

    def process_tick(self, market: MarketSnapshot, portfolio: PortfolioState) -> OrderProposal | None:
        market_decision = self.safety.review_market(market)
        if not market_decision.approved:
            self._audit("market_block", "WARN", market_decision.reason)
            return None

        signal = self.strategy.generate_signal(market)
        if not signal:
            self._audit("no_signal", "INFO", "strategy returned no signal")
            return None

        order = self.execution.signal_to_order(signal, market.price, portfolio)
        if not order:
            self._audit("order_not_created", "INFO", "execution planner returned none")
            return None

        edge_decision = self.safety.net_edge_check(order.expected_edge_bps)
        if not edge_decision.approved:
            self._audit("order_block", "WARN", edge_decision.reason)
            return None

        gross_exposure = sum(abs(qty) * market.price for qty in portfolio.positions.values())
        order_decision = self.safety.review_order(order, portfolio, gross_exposure)
        if not order_decision.approved:
            self._audit("order_block", "WARN", order_decision.reason)
            return None

        if self.config.policy.require_manual_approval and not self.config.policy.autonomous_execution:
            self._audit("manual_review_required", "INFO", f"proposed {order.side} {order.quantity:.4f} {order.symbol}")
            return order

        self._audit("order_approved", "INFO", f"approved {order.side} {order.quantity:.4f} {order.symbol}")
        return order
