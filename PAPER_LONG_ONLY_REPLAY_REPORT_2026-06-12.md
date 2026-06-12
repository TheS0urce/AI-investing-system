# Paper Long-Only Replay Report - 2026-06-12

## Scope

This report replays the complete proposal-bearing `$100` paper-watch session from `2026-06-10` through the current long-only safety code. It is read-only and does not submit orders.

## Replay Input

- Source window: `2026-06-10T13:30:00+00:00` through `2026-06-10T15:00:00+00:00`
- Replayed evaluated ticks: `150`
- Simulated cash / equity / peak equity: `$100 / $100 / $100`
- Positions: empty
- Short sales allowed: `False`

## Results

- Manual-review proposals: `23`
- BUY proposals: `23`
- SELL proposals: `0`
- Naked SELL signals blocked with `short_sale_disabled`: `5`
- Proposal symbols: `NVDA=11`, `QQQ=11`, `MSFT=1`
- Proposal notional range: `$1.301572` to `$2.00`
- Paper orders submitted: `0`

## Residual Gates

- `insufficient_net_edge_after_costs`: `51`
- `spread_too_wide`: `40`
- `insufficient_liquidity`: `31`

## Conclusion

The long-only guard behaves correctly on a complete real-market sample: valid `$100` BUY proposals remain available for manual review, while every naked fractional SELL signal is blocked before submission.
