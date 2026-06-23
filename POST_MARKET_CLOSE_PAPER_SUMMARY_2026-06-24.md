# Post-Market Close Paper Summary - 2026-06-24

## Scope

This summary covers the bounded paper preauthorization run for the 2026-06-23 U.S. trading session, reviewed on 2026-06-24 NZ local time. It documents the first broker-reached preauthorized paper attempt and the follow-up compatibility fix. Live routing remained disabled.

## LaunchAgent Run

- Latest completed session: `2026-06-23`
- Completed at: `2026-06-24T02:11:18.981782+12:00`
- Completion marker: `WATCH-COMPLETED`
- Return code: `0`
- Proposal count captured by scheduler: `56`
- Preauthorized submit events: `1`

## Broker Response

- Submit marker: `PREAUTHORIZED-SUBMIT-BLOCKED`
- Cycle: `20`
- Symbol: `NVDA`
- Broker response: `alpaca_order_http_error:422`
- Broker message: `fractional orders must be simple orders`

## Safety State

- Preauthorization active after run: `False`
- Operational errors: `1`
- Gross exposure: `$0.0`
- Entries this session: `0`
- Open paper orders: `0`
- Broker mode: `paper`
- Live routing enabled: `False`

## Fix Applied

The preauthorized paper submit endpoint now routes bounded fractional entries as simple Alpaca limit orders instead of broker bracket orders. It still calculates the planned stop-loss and take-profit levels and returns them as `protective_exit` with `protection_mode=planned_application_managed_exit_pending_verification`.

## Remaining Blocker

The broker-entry compatibility blocker is addressed in code, but protective exits for fractional entries still need paper verification. Do not treat the system as live-ready until a simple fractional paper entry is accepted and the application-managed exit workflow is proven.
