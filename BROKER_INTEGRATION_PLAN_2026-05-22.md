# Broker Integration Plan - 2026-05-22

## Decision

Default Stage-1 candidate: **Alpaca paper trading** for US equities/ETFs.

Rationale:
- API-native trading workflow.
- Free paper trading is available to Alpaca users.
- Paper environment is explicitly intended for testing code before going live.
- Fractional share support can fit a small-account rollout better than whole-share-only workflows.

Alternatives:
- **Tradier sandbox**: viable paper/sandbox API with delayed market data; useful if options workflows become a priority later.
- **Interactive Brokers**: broad and mature, but higher integration complexity; better reserved for a later, more advanced deployment stage.

Sources checked:
- Alpaca Trading API docs: https://docs.alpaca.markets/docs/trading-api
- Alpaca Python trading SDK docs: https://alpaca.markets/sdks/python/trading.html
- Tradier trading API docs: https://docs.tradier.com/docs/trading
- Tradier endpoint docs: https://docs.tradier.com/docs/endpoints

## Stage Gate

Current state remains:
- Mac-only local shadow deployment.
- No live broker routing.
- No broker credentials committed.
- No trade permissions enabled in this repository.

Stage-1 broker integration must start with **paper-only** credentials.

## Required Before Paper Integration

1. Create paper broker account.
2. Enable MFA on broker account and email account.
3. Generate paper-only API credentials.
4. Store credentials only in local `.env`.
5. Confirm `.env` is ignored by git.
6. Add paper adapter in code with a fail-closed default.
7. Add tests for:
   - missing credentials,
   - paper endpoint selection,
   - disabled live mode,
   - order preview/dry-run behavior,
   - broker error handling.
8. Run local validation:
   - `./scripts/check.sh`
   - health endpoint,
   - auth rejection without key,
   - authenticated summary,
   - paper broker account/readiness check.

## Paper-Only Configuration Draft

Use placeholders only; do not commit real values.

```bash
BROKER_PROVIDER=alpaca
BROKER_MODE=paper
BROKER_LIVE_ENABLED=false
ALPACA_PAPER_API_KEY=replace_me
ALPACA_PAPER_SECRET_KEY=replace_me
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets
```

When ready, configure local paper credentials with:

```bash
./scripts/configure_alpaca_paper.sh
./scripts/install_launch_agent.sh
./scripts/broker_readiness.sh
python scripts/alpaca_env_sanity.py
python scripts/check_alpaca_paper_account.py
```

## NO-GO Conditions

Do not proceed to live broker routing if any are true:
- broker mode is not explicitly `paper`;
- live mode is enabled;
- credentials are missing or committed;
- tests fail;
- endpoint smoke checks fail;
- manual approval is disabled;
- autonomous execution is enabled;
- kill switch procedure has not been tested;
- account reconciliation procedure has not been written.

## Later Live-Routing Promotion Criteria

Live routing is a separate stage and requires:
- at least one clean paper/shadow review window;
- documented order reconciliation;
- incident drill evidence;
- broker terms/API permission review;
- tax/reporting review;
- explicit signed GO decision in the runbook.
