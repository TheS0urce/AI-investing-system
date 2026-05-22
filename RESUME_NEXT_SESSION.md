# Resume Next Session

Trigger phrase: **Let's continue**

## Current State

- Mac API service: running via LaunchAgent `com.aiinvesting.api`
- API URL: `http://127.0.0.1:8001`
- Dashboard apps: `~/Applications/AI Investment`
- Broker: Alpaca paper
- Broker readiness: `ALPACA-PAPER-READY`
- Market data: Alpaca stock snapshots via `https://data.alpaca.markets`, default feed `iex`
- Live routing: `false`
- Autonomous execution: `false`
- Manual approval required: `true`
- Open paper orders: `[]`
- Final validation: `./scripts/check.sh` passed with 39 tests

## Completed Today

- Mac-only deployment and launcher apps
- Alpaca paper credentials configured locally
- Read-only paper account check
- Paper order preview
- Guarded manual paper submit
- Paper order reconciliation
- Guarded paper order cancellation
- Paper order cancellation verified, no open paper orders remain
- Read-only Alpaca market-data snapshot adapter
- Real-time paper strategy preview endpoint
- Read-only paper account endpoint
- Strategy preview can size from read-only paper account state
- Dashboard real-time paper preview controls
- LaunchAgent restarted with paper market-data endpoints live

## Evidence Files

- `OPERATIONS_SNAPSHOT_2026-05-22.md`
- `ALPACA_PAPER_VERIFICATION_2026-05-22.md`
- `PAPER_ORDER_SUBMISSION_2026-05-22.md`
- `PAPER_ORDER_RECONCILIATION_2026-05-22.md`
- `PAPER_ORDER_CANCEL_2026-05-22.md`
- `PAPER_MARKET_DATA_PREVIEW_2026-05-23.md`

## First Commands Tomorrow

```bash
cd "/Users/michielburger/Claude Code/AI-investing-system"
git status --short --branch
./scripts/check.sh
.venv/bin/python scripts/check_alpaca_market_data.py
curl -s http://127.0.0.1:8001/dashboard/summary -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/account" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/orders?status=open&limit=20" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/strategy_preview?symbol=QQQ&feed=iex&use_paper_account=true" -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

## Next Technical Goal

Continue real-time paper trading, not live trading:

1. Add timed polling/watch mode for selected paper symbols.
2. Improve strategy signal quality before any live trading discussion.
3. Add dashboard display for watch-mode history and blocked/proposed actions.
4. Keep paper submit manual-only behind exact confirmation phrase.
5. Run paper submit/reconcile/cancel drill again.

## Boundaries

- Do not enable live credentials.
- Do not enable live routing.
- Do not enable autonomous broker submission.
- Do not submit paper orders automatically from the strategy pipeline until a separate GO decision.
