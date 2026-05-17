# Operations Snapshot — 2026-05-11

## Environment
- Host: Mac mini
- Mode: Controlled launch (manual-review safety posture)
- Service manager: launchctl (`com.aiinvesting.api`)

## Validation results (2026-05-11)
- Check script: pass (`./scripts/check.sh`)
- Health endpoint: 200 (`/health`)
- Unauthorized simulate: 401 (`/simulate_tick` without API key)
- Authorized simulate: 200 (`/simulate_tick` with API key)
- Dashboard summary endpoint: 200 JSON (`/dashboard/summary`)
- Working tree status: clean
- `.env` secret handling: ignored, untracked

## Operational status
- Decision: **GO (controlled mode)**
- Rationale: all go/no-go gates passed.

## Current risk posture
- Conservative defaults retained.
- Human-in-the-loop approval posture retained.
- No autonomous scale increase without monthly governance review.

## Next review checkpoints
- Weekly review due: 2026-05-15
- Monthly governance review due: 2026-06-08

## Notes
- Continue daily health/auth checks.
- Continue weekly logs + blocked-reason review.

# OPERATIONS SNAPSHOT UPDATE (2026-05-17T07:07:31Z)
commit_sha: 6d15c83173b92d7e66db8e611abbaec6ee1bf37f
health_status: 200
simulate_tick_unauthorized_status: 401
simulate_tick_authorized_status: 200
dashboard_summary_status: 404
health_body: {"status":"ok","time":"2026-05-17T07:07:31.060420+00:00"}
simulate_tick_unauthorized_body: {"detail":"invalid api key"}
simulate_tick_authorized_body: {"order_proposal":null,"latest_audit":{"at":"2026-05-17T07:07:31.091302+00:00","event":"order_block","severity":"WARN","details":"insufficient_net_edge_after_costs"}}
dashboard_summary_body: {"detail":"Not Found"}
