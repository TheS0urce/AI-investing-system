# Operations Snapshot - 2026-05-22

## Stage

- Stage: Day-0 local shadow deployment
- Host: Mac Mini
- API service: macOS LaunchAgent `com.aiinvesting.api`
- API URL: `http://127.0.0.1:8001`
- Dashboard: on-demand Streamlit launcher
- Capital status: `$100` available, not live-routed
- Execution mode: shadow/simulation only

## Deployment Evidence

- LaunchAgent status: `29170 -15 com.aiinvesting.api`
- Health check: `{"status":"ok","time":"2026-05-22T00:18:57.703575+00:00"}`
- Dashboard summary:
  - `status`: `ok`
  - `manual_approval_required`: `true`
  - `autonomous_execution`: `false`
  - `kill_switch`: `false`
- $100 shadow tick:
  - `order_proposal`: `null`
  - latest audit event: `order_block`
  - latest audit detail: `insufficient_net_edge_after_costs`

## GO/NO-GO

- GO: Mac-only persistent local shadow deployment.
- NO-GO: live broker order routing.

## Notes

- Broker selection is intentionally deferred until the broker-integration stage.
- Local Mac launcher apps are grouped under `~/Applications/AI Investment`.
- The system remains safety-first: no autonomous execution and no live broker route.
