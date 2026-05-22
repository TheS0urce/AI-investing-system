# Resume Next Session

Trigger phrase: **Let's continue**

## Current State

- Mac API service: running via LaunchAgent `com.aiinvesting.api`
- API URL: `http://127.0.0.1:8001`
- Dashboard apps: `~/Applications/AI Investment`
- Broker: Alpaca paper
- Broker readiness: `ALPACA-PAPER-READY`
- Live routing: `false`
- Autonomous execution: `false`
- Manual approval required: `true`
- Open paper orders: `[]`
- Final validation: `./scripts/check.sh` passed with 31 tests

## Completed Today

- Mac-only deployment and launcher apps
- Alpaca paper credentials configured locally
- Read-only paper account check
- Paper order preview
- Guarded manual paper submit
- Paper order reconciliation
- Guarded paper order cancellation
- Paper order cancellation verified, no open paper orders remain

## Evidence Files

- `OPERATIONS_SNAPSHOT_2026-05-22.md`
- `ALPACA_PAPER_VERIFICATION_2026-05-22.md`
- `PAPER_ORDER_SUBMISSION_2026-05-22.md`
- `PAPER_ORDER_RECONCILIATION_2026-05-22.md`
- `PAPER_ORDER_CANCEL_2026-05-22.md`

## First Commands Tomorrow

```bash
cd "/Users/michielburger/Claude Code/AI-investing-system"
git status --short --branch
./scripts/check.sh
curl -s http://127.0.0.1:8001/dashboard/summary -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/orders?status=open&limit=20" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

## Next Technical Goal

Implement real-time paper trading, not live trading:

1. Add market-data source selection for paper stage.
2. Add read-only market data fetch/polling.
3. Feed market snapshots into the existing strategy/safety pipeline.
4. Display strategy proposal in dashboard.
5. Keep paper submit manual-only behind exact confirmation phrase.
6. Run paper submit/reconcile/cancel drill again.

## Boundaries

- Do not enable live credentials.
- Do not enable live routing.
- Do not enable autonomous broker submission.
- Do not submit paper orders automatically from the strategy pipeline until a separate GO decision.
