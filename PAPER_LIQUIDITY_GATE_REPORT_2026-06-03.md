# Paper Liquidity Gate Report - 2026-06-03

## Scope

This report is a read-only liquidity threshold diagnostic. It does not change risk gates, submit orders, or enable live routing.

## Totals

- Generated at: `2026-06-03T03:00:55.838792+00:00`
- Since: `2026-06-02T13:30:45.554280+00:00`
- Evaluated events: `30`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Volume

- Volume min / max: `5246.0` / `581718.0`

## Threshold Pass Counts

- >= 25000.0: `25`
- >= 50000.0: `20`
- >= 75000.0: `9`
- >= 100000.0: `1`

## Audit Details

- insufficient_liquidity: `29`
- insufficient_net_edge_after_costs: `1`

## Operator Conclusion

Opening-window liquidity blocks are sensitive to the volume threshold and the data source's intraday volume semantics. Treat this as diagnostic evidence only; do not lower risk gates without more paper sessions.
