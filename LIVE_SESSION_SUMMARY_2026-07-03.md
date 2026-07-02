# First Bounded Live Session Summary - 2026-07-03 NZT

## Outcome

The first bounded real-money session completed its full entry-to-exit lifecycle.
Execution and safety controls worked, while the two trades produced a small loss.

## Broker Evidence

- U.S. session: `2026-07-02`
- Eligible proposals observed: `59`
- Live entries submitted: `2`
- Symbol: `NVDA`
- Entry notionals: `$4.19` and `$3.97`
- Entry prices: `$198.65` and `$198.57`
- Exit reason: `stop_loss`
- Exit fill prices: `$195.454` and `$195.452`
- Realized P&L: `-$0.067465` and `-$0.062377`
- Total recorded realized P&L: `-$0.129842`
- Closing portfolio value: `$298.96`
- Open orders after session: `0`
- Open positions after session: `0`
- Active protective exits after session: `0`
- Operational errors: `0`

## Operational Assessment

The scheduler generated proposals, respected the two-entry limit, submitted
fractional live entries, persisted protective plans, monitored both positions,
triggered stop-loss exits, reconciled broker-confirmed fills, and updated realized
performance. The account finished flat and fully in cash.

## Risk-Control Learning

Both entries were in NVDA at similar prices and exited together. Although total
exposure remained small, this was one correlated trade idea expressed twice.

The next-session controls now:

- Reject a new entry when that symbol already has an open position.
- Limit entries to the remaining consecutive-loss budget.
- Allow only one entry when two consecutive losses have already occurred.
- Cap progressed session entries at the three-loss pause threshold.

## Next Session

The current authorization expires before the next U.S. session. No further live
trade can occur without a fresh preflight and explicit `AUTHORIZE_BOUNDED_LIVE`.
If reauthorized, the next session is limited to one entry unless performance state
changes.
