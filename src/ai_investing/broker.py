from __future__ import annotations

from dataclasses import dataclass

from .config import BrokerConfig


@dataclass(frozen=True)
class BrokerReadiness:
    provider: str
    mode: str
    live_enabled: bool
    ready: bool
    status: str
    reason: str


def broker_readiness(config: BrokerConfig) -> BrokerReadiness:
    provider = config.provider.strip().lower()
    mode = config.mode.strip().lower()

    if config.live_enabled:
        return BrokerReadiness(
            provider=provider,
            mode=mode,
            live_enabled=True,
            ready=False,
            status="NO-GO",
            reason="live_broker_routing_disabled_for_current_stage",
        )

    if provider in {"", "none"} or mode in {"", "none"}:
        return BrokerReadiness(
            provider=provider or "none",
            mode=mode or "none",
            live_enabled=False,
            ready=False,
            status="PAPER-BROKER-NOT-CONFIGURED",
            reason="safe_for_current_shadow_deployment",
        )

    if mode != "paper":
        return BrokerReadiness(
            provider=provider,
            mode=mode,
            live_enabled=False,
            ready=False,
            status="NO-GO",
            reason="broker_mode_must_be_paper",
        )

    if provider != "alpaca":
        return BrokerReadiness(
            provider=provider,
            mode=mode,
            live_enabled=False,
            ready=False,
            status="NO-GO",
            reason="unsupported_broker_provider",
        )

    if config.paper_base_url != "https://paper-api.alpaca.markets":
        return BrokerReadiness(
            provider=provider,
            mode=mode,
            live_enabled=False,
            ready=False,
            status="ALPACA-PAPER-NOT-READY",
            reason="paper_base_url_not_configured",
        )

    return BrokerReadiness(
        provider=provider,
        mode=mode,
        live_enabled=False,
        ready=True,
        status="ALPACA-PAPER-READY",
        reason="paper_endpoint_configured_live_routing_disabled",
    )
