# Post-Market-Close Paper Summary

Generated for operator review on `2026-06-13` (`Pacific/Auckland`), after the completed long-only `$100`-equivalent read-only paper watch for the `2026-06-12` U.S. session.

## Latest Completed Long-Only `$100`-Equivalent Paper Watch

- Session window: `2026-06-12T13:45:36.541905+00:00` through `2026-06-12T13:50:09.377088+00:00`.
- Expected versus completed ticks: `75` planned (`15` cycles across `SPY`, `QQQ`, `AAPL`, `MSFT`, `NVDA`) versus `75` completed.
- Watch status: complete read-only watchlist run, all ticks `EVALUATED`, auto-submit disabled throughout.
- Symbol coverage: `15` ticks each for `SPY`, `QQQ`, `AAPL`, `MSFT`, and `NVDA` on `iex`.

## Proposals And Long-Only Guard

- BUY manual-review proposals: `0`.
- `short_sale_disabled` blocks: `25`.
- Proposal notional range: none in the latest completed session because no proposal cleared all gates.
- Interpretation: the long-only guard blocked naked SELL paths safely, but no BUY signal reached manual review in this sample.

## Residual Market Gates

- `insufficient_net_edge_after_costs`: `27`
- `insufficient_liquidity`: `15`
- `spread_too_wide`: `8`
- Residual gate conclusion: edge shortfall remained the primary blocker after the long-only guard removed naked fractional SELL paths.

## Current Paper State

- Current paper readiness: `PAPER-GO` with `11/11` checks passing.
- Broker state: `ALPACA-PAPER-READY`, paper mode, live routing disabled, autonomous execution disabled, manual approval required.
- Current open paper orders: `0`.
- Latest safe next action: `WAIT_FOR_MARKET_OPEN`.
- Next paper market open: `2026-06-15T09:30:00-04:00` (`2026-06-16T01:30:00+12:00` operator time).

## Next Launch Action

- Keep the system in paper mode with manual approval only.
- Before the next U.S. open, run `.venv/bin/python scripts/paper_market_open_preflight.py`.
- If preflight returns `PAPER-MARKET-OPEN-GO`, launch the same guarded long-only `$100` watch configuration for the next open-window sample; do not submit any order and do not enable live routing.
