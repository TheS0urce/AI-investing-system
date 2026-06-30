from src.ai_investing.broker import broker_readiness, live_broker_readiness
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


def test_broker_readiness_requires_paper_credentials():
    status = broker_readiness(
        BrokerConfig(
            provider="alpaca",
            mode="paper",
            live_enabled=False,
            paper_base_url="https://paper-api.alpaca.markets",
        )
    )
    assert not status.ready
    assert status.status == "ALPACA-PAPER-NOT-READY"
    assert status.reason == "paper_credentials_not_configured"


def test_broker_readiness_allows_alpaca_paper_config_only():
    status = broker_readiness(
        BrokerConfig(
            provider="alpaca",
            mode="paper",
            live_enabled=False,
            paper_base_url="https://paper-api.alpaca.markets",
            paper_api_key_present=True,
            paper_secret_key_present=True,
        )
    )
    assert status.ready
    assert status.status == "ALPACA-PAPER-READY"
    assert status.reason == "paper_credentials_present_live_routing_disabled"


def test_live_broker_readiness_is_disabled_by_default():
    status = live_broker_readiness(BrokerConfig(provider="alpaca", mode="paper"))

    assert not status.ready
    assert status.status == "LIVE-DISABLED"


def test_live_broker_readiness_rejects_non_exact_domain():
    status = live_broker_readiness(
        BrokerConfig(
            provider="alpaca",
            mode="live",
            live_enabled=True,
            live_base_url="https://paper-api.alpaca.markets",
            live_api_key_present=True,
            live_secret_key_present=True,
        )
    )

    assert not status.ready
    assert status.reason == "live_base_url_not_exact"


def test_live_broker_readiness_requires_separate_credentials():
    status = live_broker_readiness(
        BrokerConfig(
            provider="alpaca",
            mode="live",
            live_enabled=True,
            live_base_url="https://api.alpaca.markets",
        )
    )

    assert not status.ready
    assert status.reason == "live_credentials_not_configured"


def test_live_broker_readiness_accepts_exact_enabled_configuration():
    status = live_broker_readiness(
        BrokerConfig(
            provider="alpaca",
            mode="live",
            live_enabled=True,
            live_base_url="https://api.alpaca.markets",
            live_api_key_present=True,
            live_secret_key_present=True,
        )
    )

    assert status.ready
    assert status.status == "ALPACA-LIVE-READY"
