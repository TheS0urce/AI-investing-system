# Post-Market Close Paper Summary - 2026-06-25

## Scope

This summary covers the continuation work after the 2026-06-24 U.S. paper observation run. Live routing remained disabled. Bounded paper preauthorization was not reactivated during this work.

## Overnight Evidence

- Latest completed session: `2026-06-24`
- Completed at: `2026-06-25T02:13:17.941183+12:00`
- Watch completion: `WATCH-COMPLETED`
- Scheduler proposal count: `7`
- Preauthorized submit events: `1`
- Submit result: `PREAUTHORIZED-SUBMIT-BLOCKED`
- Block reason: `operational_error_pause`
- Exposure after run: `$0.0`
- Entries after run: `0`

## Fixes Added

- Added Alpaca paper position parsing and `/v2/positions` support.
- Added persistent paper protective-exit plans at `state/paper_protective_exits.json`.
- A successful bounded fractional paper entry now records its planned stop-loss, take-profit, and max holding window.
- Added `/broker/paper/protective_exits/check`.
- Added `scripts/paper_protective_exit_check.py`.
- Updated the market-open LaunchAgent runner so every 5-minute invocation checks protective exits before schedule decisions.
- Updated the runner to disable preauthorized submit for a watch run when authorization is inactive or paused.

## Verification

- Focused tests passed: app broker, Alpaca adapter, scheduled runner.
- Full `./scripts/check.sh` passed.
- API LaunchAgent reloaded successfully.
- Manual protective-exit probe returned `NO-ACTIVE-PROTECTIVE-EXITS`.
- Manual scheduled probe returned `PROTECTIVE-EXIT-CHECK` followed by closed-market `SCHEDULE-CHECK`.

## Current State

- Preauthorization active: `False`
- Operational errors: `1`
- Open paper orders: `0`
- Active protective exits: `0`
- Broker mode: `paper`
- Live routing enabled: `False`

## Next Step

The application-managed fractional exit workflow is now implemented and loaded. The next paper test can be re-armed only after explicit operator authorization with `AUTHORIZE_BOUNDED_PAPER`.
