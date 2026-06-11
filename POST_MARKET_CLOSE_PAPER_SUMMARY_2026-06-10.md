# Post-Market-Close Paper Summary

Generated for operator review on `2026-06-11` (`Pacific/Auckland`), after the scheduled paper watchlist attempt for the `2026-06-10` U.S. session.

## Latest Read-Only Paper Watch

- Scheduled paper watchlist outcome: successful read-only market-open watch.
- Latest session window: `2026-06-10T13:30:48.131558+00:00` through `2026-06-10T14:05:14.128766+00:00`.
- Latest session totals: `150` ticks, `150` evaluated, `28` manual-review paper proposals, `122` blocked or no-proposal ticks.
- Latest session symbol coverage: `30` ticks each for `SPY`, `QQQ`, `AAPL`, `MSFT`, and `NVDA` on `iex`.
- Archive watch totals from [`/Users/michielburger/Claude Code/AI-investing-system/PAPER_WATCH_REPORT_2026-06-10.md`](/Users/michielburger/Claude%20Code/AI-investing-system/PAPER_WATCH_REPORT_2026-06-10.md): `482` total ticks, `47` proposals, `435` blocked or no-proposal ticks, `auto_submit_enabled=false`.

## Proposal Blocker Status

- Proposal blocker status: cleared for the latest sample. Proposal generation worked in live paper-watch conditions without enabling routing or submission.
- Residual blocker mix in the latest session: `51` `insufficient_net_edge_after_costs`, `40` `spread_too_wide`, and `31` `insufficient_liquidity`.
- Proposal quality in the latest session: expected edge ranged from `9.1110` to `14.0` bps, above the configured `9.0` bps requirement on proposal ticks.
- Proposal distribution in the latest session: `QQQ=12`, `NVDA=11`, `AAPL=3`, `SPY=1`, `MSFT=1`; `BUY=23`, `SELL=5`.
- Proposal notional range under the `$100` profile: `$1.301572` to `$2.00`.
- Launch-stage hardening after review: short sales are disabled by default; naked fractional SELL proposals are blocked, while SELL orders within an owned position remain allowed.

## Watch Quality

- Watch quality: strong for proposal discovery and still mixed on weaker ticks.
- Latest session market ranges: `volume_min=10510`, `volume_max=5608889`, `spread_bps_max=441.8735`.
- Interpretation: the watchlist is now producing real manual-review opportunities, but spread and liquidity conditions still reject a large share of the sample.

## Paper Ops Evidence

- Health evidence: local API health returned `ok` during this run.
- Preflight evidence from `paper_next_action.py`: `readiness_status=PAPER-GO`, `strategy_quality_status=STRATEGY-QUALITY-OK`, `open_orders=0`, `auto_submit_enabled=false`, `live_trading_approved=false`.
- Current market-session status: `WAIT_FOR_MARKET_OPEN`; next paper market open is `2026-06-12T01:30:00+12:00` (`Pacific/Auckland`).
- Direct consolidated ops snapshot refresh failed closed with `network_error:[Errno 1] Operation not permitted`, so no new sanitized `PAPER_OPS_EVIDENCE_2026-06-10.md` file was written from this sandbox.

## Safety Guardrails

- No paper order was submitted.
- Open paper orders remain `0`.
- Auto-submit stayed disabled throughout the latest session history.
- Live routing was not approved or enabled.
- This summary is read-only and does not authorize live routing or paper order submission.
- `PAPER_CAPITAL_PROFILE_REPORT_2026-06-10.md` records the representative sizing evidence and long-only launch guard.
- Full repository validation passed with `126` tests.

## Next Recommended Action

- Next safe operator action: retain paper mode and validate the long-only watch path at the next market open.
- Before the next watch window, run `.venv/bin/python scripts/paper_market_open_preflight.py`.
- If preflight returns `PAPER-MARKET-OPEN-GO`, run the guarded read-only watchlist and keep manual approval in place. Do not submit any order or enable live routing.
