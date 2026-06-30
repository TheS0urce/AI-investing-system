from pydantic import BaseModel, Field


class RiskConfig(BaseModel):
    max_order_notional: float = Field(default=2_000.0, gt=0)
    allow_short_sales: bool = False
    max_symbol_exposure_pct: float = Field(default=0.20, gt=0, le=1)
    max_gross_exposure_pct: float = Field(default=0.90, gt=0, le=1)
    max_drawdown_pct: float = Field(default=0.12, gt=0, le=1)
    max_daily_loss_pct: float = Field(default=0.02, gt=0, le=1)
    max_leverage: float = Field(default=1.0, ge=0)
    max_spread_bps: float = Field(default=30.0, ge=0)
    min_volume_24h: float = Field(default=100_000.0, ge=0)
    max_volatility_30d: float = Field(default=0.12, ge=0)
    cooldown_after_losses: int = Field(default=3, ge=0)


class CostConfig(BaseModel):
    fee_bps: float = Field(default=2.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    min_net_edge_bps: float = Field(default=2.0)


class PolicyConfig(BaseModel):
    autonomous_execution: bool = False
    require_manual_approval: bool = True
    kill_switch: bool = False


class BrokerConfig(BaseModel):
    provider: str = "none"
    mode: str = "none"
    live_enabled: bool = False
    paper_base_url: str | None = None
    market_data_base_url: str | None = None
    market_data_feed: str = "iex"
    paper_api_key_present: bool = False
    paper_secret_key_present: bool = False
    live_base_url: str | None = None
    live_api_key_present: bool = False
    live_secret_key_present: bool = False


class SystemConfig(BaseModel):
    risk: RiskConfig = RiskConfig()
    costs: CostConfig = CostConfig()
    policy: PolicyConfig = PolicyConfig()
    broker: BrokerConfig = BrokerConfig()
