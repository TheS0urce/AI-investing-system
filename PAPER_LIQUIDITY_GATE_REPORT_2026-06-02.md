# Paper Liquidity Gate Report - 2026-06-02

## Scope

This report is a read-only liquidity threshold diagnostic. It does not change risk gates, submit orders, or enable live routing.

## Totals

- Generated at: `2026-06-02T04:08:23.274785+00:00`
- Since: `2026-06-01T13:31:06.389097+00:00`
- Evaluated events: `30`
- Auto submit enabled: `False`
- Live trading approved: `False`

## Volume

- Volume min / max: `8942.0` / `68550.0`

## Threshold Pass Counts

- >= 25000.0: `24`
- >= 50000.0: `13`
- >= 75000.0: `0`
- >= 100000.0: `0`

## Audit Details

- insufficient_liquidity: `30`

## Operator Conclusion

Opening-window liquidity blocks are sensitive to the volume threshold and the data source's intraday volume semantics. Treat this as diagnostic evidence only; do not lower risk gates without more paper sessions.
