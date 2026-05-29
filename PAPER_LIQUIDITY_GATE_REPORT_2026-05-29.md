# Paper Liquidity Gate Report - 2026-05-29

## Scope

This report is a read-only liquidity threshold diagnostic. It does not change risk gates, submit orders, or enable live routing.

## Totals

- Generated at: `2026-05-29T21:42:03.530504+00:00`
- Since: `2026-05-29T13:00:00+00:00`
- Evaluated events: `30`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Volume

- Volume min / max: `7499.0` / `712765.0`

## Threshold Pass Counts

- >= 25000.0: `24`
- >= 50000.0: `19`
- >= 75000.0: `10`
- >= 100000.0: `1`

## Audit Details

- insufficient_liquidity: `29`
- insufficient_net_edge_after_costs: `1`

## Operator Conclusion

Opening-window liquidity blocks are sensitive to the volume threshold and the data source's intraday volume semantics. Treat this as diagnostic evidence only; do not lower risk gates without more paper sessions.
