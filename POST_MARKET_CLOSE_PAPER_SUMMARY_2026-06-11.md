# Post-Market-Close Paper Summary

Generated for operator review on `2026-06-12` (`Pacific/Auckland`), after the scheduled paper watchlist attempt for the `2026-06-11` U.S. session.

## Latest Read-Only `$100`-Equivalent Paper Watch

- Scheduled paper watchlist outcome: successful read-only market-open watch.
- Latest session window: `2026-06-11T13:30:47.330135+00:00` through `2026-06-11T13:37:44.100245+00:00`.
- Latest session totals: `35` ticks, `35` evaluated, `0` manual-review proposals, `35` blocked or no-proposal ticks.
- Latest session symbol coverage: `7` ticks each for `SPY`, `QQQ`, `AAPL`, `MSFT`, and `NVDA` on `iex`.
- Residual blocker mix in the latest session: `18` `insufficient_liquidity`, `12` `spread_too_wide`, and `5` `insufficient_net_edge_after_costs`.
- Completion status: partial. The unattended job captured `7` of the configured `30` cycles because its runtime window was shorter than the launcher's configured duration.

## BUY Proposals And Long-Only SELL Guard

- BUY manual-review proposals in the latest session: `0`.
- Naked SELL signals blocked by the long-only guard in the partial latest session: `0`, because no negative signal passed the earlier market and edge gates.
- Deterministic replay evidence from `PAPER_LONG_ONLY_REPLAY_REPORT_2026-06-12.md`: all `150` ticks from the complete proposal-bearing `$100` session were re-evaluated under current code, producing `23` BUY manual-review proposals, `0` SELL proposals, and `5` `short_sale_disabled` blocks.
- Proposal notional range in the latest session: none, because no proposal passed all gates.
- Most recent proposal-bearing `$100` notional range: `$1.301572` to `$2.00`.

## Watch Quality

- Watch quality: weak for proposal discovery in the latest sample, with market conditions dominated by liquidity and spread failures.
- Latest session market ranges: `volume_min=6086.0`, `volume_max=4910869.0`, `spread_bps_max=595.5334987593052`.
- Interpretation: the long-only launch path stayed safe, but this specific `2026-06-11` sample did not reproduce the stronger proposal quality seen on `2026-06-10`.

## Paper Readiness And Orders

- Fresh direct readiness check: `PAPER-GO`, all `11/11` checks passed.
- Current broker state: paper mode, `ALPACA-PAPER-READY`, live routing disabled, autonomous execution disabled, manual approval required.
- Current open paper orders: `0`.
- Repository notes in [`/Users/michielburger/Claude Code/AI-investing-system/RESUME_NEXT_SESSION.md`](/Users/michielburger/Claude%20Code/AI-investing-system/RESUME_NEXT_SESSION.md) record that the reinstalled API includes the long-only guard and reported `ALPACA-PAPER-READY` before this final validation cycle.

## Safety Guardrails

- No paper order was submitted.
- Auto-submit remained disabled throughout the recorded watch history.
- Live routing was not approved or enabled.
- Short sales remain disabled by default.
- Fractional SELL orders cannot open short positions, and SELL quantities above owned positions are blocked.
- This summary is read-only and does not authorize paper submission or live routing.

## Next Recommended Action

- Keep the system in paper mode and retain manual approval.
- The corrected unattended watch is scheduled for Saturday `2026-06-13 01:45 Pacific/Auckland`, fifteen minutes after market open, using `15` cycles at `10`-second intervals so it finishes within the automation runtime window.
- No paper order should be submitted until the operator explicitly authorizes the strategy-generated paper lifecycle test.
