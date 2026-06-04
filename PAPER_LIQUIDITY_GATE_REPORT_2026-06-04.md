# Paper Liquidity Gate Report - 2026-06-04

## Scope

This report is a read-only liquidity threshold diagnostic. It does not change risk gates, submit orders, or enable live routing.

## Totals

- Generated at: `2026-06-04T03:46:43.156073+00:00`
- Since: `2026-06-03T13:30:40.021861+00:00`
- Evaluated events: `30`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Volume

- Volume min / max: `6466.0` / `586617.0`

## Threshold Pass Counts

- >= 25000.0: `24`
- >= 50000.0: `18`
- >= 75000.0: `14`
- >= 100000.0: `9`

## Audit Details

- insufficient_liquidity: `21`
- insufficient_net_edge_after_costs: `9`

## Operator Conclusion

Opening-window liquidity blocks are sensitive to the volume threshold and the data source's intraday volume semantics. Treat this as diagnostic evidence only; do not lower risk gates without more paper sessions.
