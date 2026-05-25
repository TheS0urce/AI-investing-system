# Scaling Policy Report - 2026-05-25

## Scope

This report validates deterministic reinvestment and ROI-tier allocation policy only. It does not call Alpaca and does not submit orders.

## Guardrails

- Status: `SCALING-POLICY-READY`
- Auto submit enabled: `no`
- Live trading approved: `no`

## Policy

- Reinvest fraction: `0.38`
- Reserve fraction: `0.62`
- Max strategy allocation pct: `0.7`
- Max external addition per review: `50.0`

## Example Decision

- Realized profit: `$100.0`
- Reinvest amount: `$38.0`
- Reserve amount: `$62.0`
- Cumulative ROI: `$1000.0`
- Allocation tier: `optimized`
- Low / medium / high risk: `0.3` / `0.55` / `0.15`
- Capped strategy capital: `$588.0`

## Operator Conclusion

Scaling remains a governed policy input. It does not increase directional aggression or enable autonomous/live execution.
