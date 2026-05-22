from src.ai_investing.broker import broker_readiness
from src.ai_investing.config import BrokerConfig


def test_broker_readiness_defaults_to_safe_shadow_status():
    status = broker_readiness(BrokerConfig())
    assert not status.ready
    assert status.status == "PAPER-BROKER-NOT-CONFIGURED"
    assert status.reason == "safe_for_current_shadow_deployment"
    assert not status.live_enabled


def test_broker_readiness_blocks_live_enabled():
    status = broker_readiness(BrokerConfig(provider="alpaca", mode="paper", live_enabled=True))
    assert not status.ready
    assert status.status == "NO-GO"
    assert status.reason == "live_broker_routing_disabled_for_current_stage"


def test_broker_readiness_blocks_non_paper_mode():
    status = broker_readiness(BrokerConfig(provider="alpaca", mode="live", live_enabled=False))
    assert not status.ready
    assert status.status == "NO-GO"
    assert status.reason == "broker_mode_must_be_paper"


def test_broker_readiness_blocks_unknown_provider():
    status = broker_readiness(BrokerConfig(provider="example", mode="paper", live_enabled=False))
    assert not status.ready
    assert status.status == "NO-GO"
    assert status.reason == "unsupported_broker_provider"


def test_broker_readiness_requires_paper_base_url():
    status = broker_readiness(BrokerConfig(provider="alpaca", mode="paper", live_enabled=False))
    assert not status.ready
    assert status.status == "ALPACA-PAPER-NOT-READY"
    assert status.reason == "paper_base_url_not_configured"


def test_broker_readiness_allows_alpaca_paper_config_only():
    status = broker_readiness(
        BrokerConfig(
            provider="alpaca",
            mode="paper",
            live_enabled=False,
            paper_base_url="https://paper-api.alpaca.markets",
        )
    )
    assert status.ready
    assert status.status == "ALPACA-PAPER-READY"
    assert status.reason == "paper_endpoint_configured_live_routing_disabled"
