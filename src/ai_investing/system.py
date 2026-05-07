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
        if not self.safety.review_market(market).approved:
            self._audit("market_block", "WARN", "market checks failed")
            return None
        signal = self.strategy.generate_signal(market)
        if not signal:
            self._audit("no_signal", "INFO", "strategy returned no signal")
            return None
        order = self.execution.signal_to_order(signal, market.price, portfolio)
        if not order:
            self._audit("order_not_created", "INFO", "execution returned none")
            return None
        self._audit("manual_review_required", "INFO", f"proposed {order.side} {order.symbol}")
        return order
