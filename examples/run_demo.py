from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ai_investing.config import SystemConfig
from src.ai_investing.models import MarketSnapshot, PortfolioState
from src.ai_investing.strategy import SimpleMomentumStrategy
from src.ai_investing.system import InvestingSystem

config = SystemConfig()
strategy = SimpleMomentumStrategy()
system = InvestingSystem(config, strategy)

portfolio = PortfolioState(cash=1000.0, equity=1000.0, peak_equity=1050.0, daily_pnl=-5.0, consecutive_losses=1, positions={"SPY": 1.0})
market = MarketSnapshot(symbol="QQQ", price=430.0, spread_bps=8.0, volume_24h=5000000, volatility_30d=0.03, timestamp=datetime.utcnow())

order = system.process_tick(market, portfolio)
print("Order proposal:", order)
print("Audit log:")
for evt in system.audit_log:
    print(f"- {evt.at.isoformat()} [{evt.severity}] {evt.event}: {evt.details}")
