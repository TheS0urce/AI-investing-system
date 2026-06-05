# Paper Liquidity Gate Report - 2026-06-05

## Scope

This report is a read-only liquidity threshold diagnostic. It does not change risk gates, submit orders, or enable live routing.

## Totals

- Generated at: `2026-06-05T01:23:15.217682+00:00`
- Since: `2026-06-04T13:31:03.780773+00:00`
- Evaluated events: `30`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Volume

- Volume min / max: `9815.0` / `142287.0`

## Threshold Pass Counts

- >= 25000.0: `26`
- >= 50000.0: `21`
- >= 75000.0: `16`
- >= 100000.0: `11`

## Audit Details

- insufficient_liquidity: `19`
- insufficient_net_edge_after_costs: `11`

## Operator Conclusion

Opening-window liquidity blocks are sensitive to the volume threshold and the data source's intraday volume semantics. Treat this as diagnostic evidence only; do not lower risk gates without more paper sessions.
