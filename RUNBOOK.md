# AI Investing System Operational Runbook

## 1) Purpose and safety model

This runbook defines how to safely operate, monitor, scale, and review the AI investing system.

Core principles:
- Capital preservation first.
- Fail closed if data/API/risk controls fail.
- Human approval by default for risk-increasing actions.
- Scale only after clean, repeatable performance windows.

## 2) Setup prerequisites

### 2.1 Legal and compliance
- Confirm your jurisdiction allows intended assets and automation mode.
- Confirm tax and reporting obligations.
- Confirm broker API terms permit algorithmic execution.

### 2.2 Bank + broker setup
1. Create a dedicated bank account for strategy cashflows.
2. Open broker account with API support.
3. Link bank account and verify transfers.
4. Enable MFA on bank, broker, and email.
5. Create API keys with least privilege.
   - Start read-only in test phase.
   - Enable trade permission only after checklist sign-off.
6. Define transfer controls:
   - Max single top-up.
   - Max weekly top-up.
   - Manual dual-check before adding external capital.

> Never store bank credentials in repo files.

### 2.3 Infrastructure and security
- Mac mini always-on, stable power/network.
- Python venv configured.
- LaunchAgent service configured.
- Logs directory configured.
- `.env` created locally and excluded from git.
- Private network access configured (e.g., Tailscale), no public port-forwarding.

## 3) Startup and runtime procedures

### 3.1 Bootstrap
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3.2 Service start
```bash
./scripts/launch_dashboard.sh
```

### 3.3 LaunchAgent verification
Install the API as a user LaunchAgent after the local launcher has passed once:
```bash
./scripts/install_launch_agent.sh
```

Verify:
```bash
launchctl list | grep com.aiinvesting.api
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8001/dashboard/summary -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Stop/remove the persistent API service:
```bash
./scripts/uninstall_launch_agent.sh
```

The dashboard remains an operator UI. Start it when needed with `./scripts/launch_dashboard.sh`, or open `http://localhost:8501` if it is already running.

### 3.4 Mac app launchers
Create clickable Mac launchers in `~/Applications/AI Investment`:
```bash
./scripts/build_macos_apps.sh
```

Created apps:
- `AI Investing Start API.app` installs/starts the persistent LaunchAgent service.
- `AI Investing Health.app` checks `http://127.0.0.1:8001/health`.
- `AI Investing Dashboard.app` starts the dashboard launcher in Terminal.
- `AI Investing Stop API.app` confirms, then removes the persistent LaunchAgent service.

The dashboard launcher Terminal should remain open while the dashboard is in use.

## 4) Final GO/NO-GO launch checklist (all must be true)

1. `./scripts/check.sh` passes.
2. `./scripts/broker_readiness.sh` returns safe paper/shadow status.
3. `/health` returns 200 + `status: ok`.
4. `/simulate_tick` without API key returns 401.
5. `/simulate_tick` with API key returns 200.
6. `git status` is clean.
7. `.env` is ignored and not tracked.
8. service is running under launchctl.
9. `/dashboard/summary` returns JSON with valid API key.
10. `/broker/status` returns paper/shadow-safe status with valid API key.

If any check fails => NO-GO. Fix and rerun full checklist.

## 5) Testing gates (anti-drift / anti-walkabout / anti-debt)

Mandatory before deploy:
```bash
./scripts/check.sh
```

Detailed checks:
```bash
pytest -q --cov=src/ai_investing --cov-report=term-missing
python examples/run_demo.py
```

Do not deploy if tests fail, coverage regresses unexpectedly, or auth behavior changes.

## 6) Weekly operations checklist

- Pull latest main and confirm clean working tree.
- Run `./scripts/check.sh`.
- Verify auth behavior (401 without key / 200 with key).
- Review logs for recurring errors.
- Review blocked-order reasons.
- Confirm kill switch state and risk limit adherence.
- Confirm no secret/artifact leakage in git.

## 7) Monthly governance checklist

- Rotate API key (or confirm age < 90 days).
- Review 30-day realized PnL (after fees), drawdown, daily-loss events.
- Apply scaling-window policy decision with documented rationale.
- Confirm reserve ratio maintained.
- Run incident drill (pause/recover/reconcile).
- Verify backup integrity; perform restore drill on cadence.
- Capture monthly sign-off and action items.

## 8) High-level profit-scaling policy

Use scaling to adjust *allowed strategy capital*, not directional aggression.

Inputs:
- starting_capital = 50
- reserve_ratio_min = 0.30
- review_window_days = 30
- max_strategy_allocation_pct = 0.70
- max_position_size_pct = 0.05
- max_daily_loss_pct = 0.02
- max_window_drawdown_pct = 0.08
- max_external_addition_per_review = 50

Decision logic:
- If operations not clean or drawdown breach:
  - no new external capital
  - no profit reinvestment
  - move profit to reserve
  - reduce risk budget
  - pause after repeated failure windows
- Else scale by profit bands with capped reinvestment/top-up.
- Always enforce hard limits (position cap, daily loss cap, alerts, exposure reduction).

## 9) Incident response

If safety breach or abnormal behavior:
1. Activate pause/kill switch.
2. Stop opening new risk.
3. Snapshot logs and context.
4. Reconcile broker positions.
5. Root-cause analysis and corrective action.
6. Resume only after successful checks and human sign-off.

## 10) Change management

For each change:
1. Branch from main.
2. Implement + test.
3. Run checks.
4. Review for secrets/artifacts.
5. Merge only when CI/checks are green.
6. Post-merge smoke test (`/health`, auth checks, dashboard summary).


## 11) Lightweight launcher (skip reinstall unless needed)

Use the launcher script for day-to-day startup. It will:
- create `.venv` if missing,
- compute a hash of requirements files,
- reinstall dependencies only when requirements changed,
- run validation checks,
- run health/auth/dashboard smoke checks,
- start Streamlit dashboard.

Run:
```bash
./scripts/launch_dashboard.sh
```

Behavior:
- First run installs dependencies.
- Subsequent runs skip dependency install unless `requirements.txt` or `requirements-dev.txt` changes.
- API defaults to `http://127.0.0.1:8001`.
- Dashboard starts at `http://localhost:8501`.

If you want a full reinstall anyway, delete the hash marker and rerun:
```bash
rm -f .venv/.deps_hash
./scripts/launch_dashboard.sh
```


## 12) Deterministic scaling module mapping

Implementation reference in code:
- `src/ai_investing/scaling.py` provides deterministic policy helpers for:
  - 38% profit reinvestment / 62% reserve split on realized profits only
  - ROI-tier allocation targets (accumulation/growth/optimized)
  - strategy-capital capping under max allocation and external addition constraints

Use this module as the policy layer; keep ML components in shadow mode until governance promotion criteria are met.

## 12.1 Broker integration staging

Broker selection is a separate stage from local deployment.

Default Stage-1 candidate is Alpaca paper trading for US equities/ETFs. Use `BROKER_INTEGRATION_PLAN_2026-05-22.md` as the checklist before adding any broker adapter code.

Required local readiness check:
```bash
./scripts/broker_readiness.sh
```

Configure paper credentials only after a broker paper account exists:
```bash
./scripts/configure_alpaca_paper.sh
./scripts/install_launch_agent.sh
.venv/bin/python scripts/alpaca_env_sanity.py
.venv/bin/python scripts/check_alpaca_paper_account.py
```

This deployment remains **NO-GO for live broker routing**. Paper order submission is manual-only, and strategy previews must not automatically submit orders.

Read-only Alpaca market data check:
```bash
.venv/bin/python scripts/check_alpaca_market_data.py
```

Fetch the read-only Alpaca paper account summary:
```bash
curl -s "http://127.0.0.1:8001/broker/paper/account" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Fetch a read-only paper market snapshot:
```bash
curl -s "http://127.0.0.1:8001/broker/paper/market_snapshot?symbol=QQQ&feed=iex" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Run a real-time paper strategy preview without submitting an order:
```bash
curl -s "http://127.0.0.1:8001/broker/paper/strategy_preview?symbol=QQQ&feed=iex&cash=100&equity=100&peak_equity=100&daily_pnl=0&consecutive_losses=0" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Run the same preview sized from read-only paper account state:
```bash
curl -s "http://127.0.0.1:8001/broker/paper/strategy_preview?symbol=QQQ&feed=iex&use_paper_account=true" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Record one read-only paper watch tick and inspect recent history:
```bash
.venv/bin/python scripts/run_paper_watch.py --symbol QQQ --feed iex --interval-seconds 5 --iterations 1
curl -s "http://127.0.0.1:8001/broker/paper/watch_history?limit=5" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Watch mode records what the strategy would have done. It does not submit orders.
History is persisted locally to `logs/paper_watch_history.jsonl`, which is gitignored runtime data.
Export watch history for review:
```bash
curl -s "http://127.0.0.1:8001/broker/paper/watch_summary?limit=500" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/watch_export?format=csv&limit=500" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8001/broker/paper/watch_export?format=jsonl&limit=500" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Generate the paper-stage readiness report:
```bash
.venv/bin/python scripts/paper_readiness_report.py
curl -s "http://127.0.0.1:8001/broker/paper/readiness?watch_limit=500" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Expected current-stage result: `PAPER-GO`. This is not live-trading approval.

Generate the consolidated read-only paper operations snapshot:
```bash
.venv/bin/python scripts/paper_ops_snapshot.py
.venv/bin/python scripts/paper_ops_evidence.py
curl -s "http://127.0.0.1:8001/broker/paper/ops_snapshot?watch_limit=500" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Expected current-stage result: `PAPER-OPS-READY`, `live_trading_approved:false`, `paper_submission_attempted:false`, and `open_orders:[]`.
The evidence helper writes a sanitized dated report such as `PAPER_OPS_EVIDENCE_YYYY-MM-DD.md`.

Paper order preview is safe to inspect because it does not submit orders:
```bash
curl -s -X POST http://127.0.0.1:8001/broker/paper/order_preview \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)" \
  -d '{"symbol":"QQQ","side":"BUY","quantity":0.01,"limit_price":430.00}'
```

Run the guarded paper order drill in no-submit mode:
```bash
.venv/bin/python scripts/paper_order_drill.py
```

Expected no-submit result: `PAPER-DRILL-READY-NO-SUBMIT`.

Run the same no-submit drill through the local API/dashboard path:
```bash
curl -s -X POST http://127.0.0.1:8001/broker/paper/order_drill \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)" \
  -d '{"symbol":"QQQ","side":"BUY","quantity":0.001,"limit_price":1.00}'
```

Expected result: `PAPER-DRILL-READY-NO-SUBMIT`, `submit_attempted:false`, and `open_orders_before:[]`.

Paper order submission is manual-only and requires an exact confirmation phrase:
```bash
curl -s -X POST http://127.0.0.1:8001/broker/paper/submit_order \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)" \
  -d '{"symbol":"QQQ","side":"BUY","quantity":0.01,"limit_price":430.00,"confirm":"SUBMIT_PAPER_ORDER"}'
```

Reconcile recent paper orders:
```bash
python scripts/list_alpaca_paper_orders.py
curl -s "http://127.0.0.1:8001/broker/paper/orders?status=all&limit=20" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)"
```

Cancel open paper orders requires explicit confirmation:
```bash
curl -s -X POST http://127.0.0.1:8001/broker/paper/cancel_orders \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep '^AI_API_KEY=' .env | cut -d= -f2-)" \
  -d '{"confirm":"CANCEL_PAPER_ORDERS"}'
```

---

## 13) Live Trading GO/NO-GO Final Sign-off (One-Page Form)

Use this form immediately before enabling any live order placement.

### 13.1 Metadata
- Date (UTC): ______________________
- Commit SHA: ______________________
- Environment: [ ] Local  [ ] Staging  [ ] Production
- Reviewer name: ___________________
- Approval authority: _______________

### 13.2 Technical Readiness (must all be YES)
- [ ] `./scripts/check.sh` passes.
- [ ] `pytest -q --cov=src/ai_investing --cov-report=term-missing` passes.
- [ ] `/health` returns 200.
- [ ] `/simulate_tick` without API key returns 401.
- [ ] `/simulate_tick` with valid API key returns 200.
- [ ] `/dashboard/summary` with valid API key returns 200.
- [ ] Current working tree is clean (`git status`).
- [ ] Tag exists for this release candidate (e.g. `preflight-go-YYYY-MM-DD`).

### 13.3 Security & Access Controls
- [ ] `AI_API_KEY` set securely (not committed to git).
- [ ] `.env` and local artifacts ignored by git.
- [ ] MFA enabled on broker, email, and banking.
- [ ] API key permissions are least-privilege.
- [ ] Rate limits enabled and verified.

### 13.4 Legal, Compliance, and Broker Terms
- [ ] Jurisdictional/legal checks completed.
- [ ] Broker API terms reviewed for automated execution.
- [ ] Tax/reporting obligations reviewed.
- [ ] Restricted products/jurisdictions blocked as required.

### 13.5 Risk & Capital Governance
- [ ] Max daily loss limit configured and tested.
- [ ] Max drawdown guardrail configured and tested.
- [ ] Position/exposure/leverage caps configured and tested.
- [ ] Kill switch tested (activate/deactivate procedure verified).
- [ ] Manual approval flow verified for risk-increasing actions.
- [ ] Capital allocation for this stage approved.
- [ ] Reserve policy and top-up limits documented.

### 13.6 Incident Readiness
- [ ] Incident runbook drill completed (pause/reconcile/resume).
- [ ] Log/audit retention path verified.
- [ ] Recovery and rollback procedure verified.
- [ ] On-call/escalation contact path documented.

### 13.7 Stage-Gate Confirmation
Select current stage and promotion decision:
- Stage 0 (local simulation): [ ] PASS [ ] FAIL
- Stage 1 (paper/shadow): [ ] PASS [ ] FAIL
- Stage 2 (limited capital live): [ ] PASS [ ] FAIL
- Stage 3 (scaled live): [ ] PASS [ ] FAIL

Promotion decision:
- [ ] GO to next stage
- [ ] NO-GO (remain at current stage)
- Reason: _____________________________________________

### 13.8 Final Decision (single checkbox required)
- [ ] **GO** — all checks above are complete and evidenced.
- [ ] **NO-GO** — do not enable live order placement.

Sign-off:
- Reviewer signature: ______________________  Date: __________
- Operator signature: ______________________  Date: __________

### 13.9 Evidence Attachment Checklist
Attach or reference:
- [ ] Command outputs for validation checks.
- [ ] Smoke endpoint outputs (status codes + response bodies).
- [ ] Commit SHA and tag.
- [ ] Risk setting snapshot.
- [ ] Incident drill notes.


---

## 14) Day-0 Launch Checklist (10 Minutes) — First Live Trades

Use this immediately before enabling first live trades.
If any step fails, mark **NO-GO** and do not proceed.

### 14.1 T-10 to T-8 min: Environment + Repo Integrity
1. Activate project environment:
   `cd "/Users/michielburger/Claude Code/AI-investing-system" && source .venv/bin/activate`
2. Confirm clean git state and known-good commit/tag:
   `git status --short && git rev-parse --short HEAD && git tag --points-at HEAD`

### 14.2 T-8 to T-6 min: Validation Gate
`./scripts/check.sh && python -m pytest -q --cov=src/ai_investing --cov-report=term-missing`

### 14.3 T-6 to T-4 min: Secrets + Policy Gate
`python -c "import os; print('AI_API_KEY set:', bool(os.getenv('AI_API_KEY')))"`

### 14.4 T-4 to T-2 min: API Smoke Gate
`curl -i http://127.0.0.1:8001/health`
`curl -i -X POST http://127.0.0.1:8001/simulate_tick -H "Content-Type: application/json" -d '{}'`
`curl -i -X POST http://127.0.0.1:8001/simulate_tick -H "Content-Type: application/json" -H "X-API-Key: $AI_API_KEY" -d '{}'`
`curl -i http://127.0.0.1:8001/dashboard/summary -H "X-API-Key: $AI_API_KEY"`

Pass criteria: 200 / 401 / 200 / 200.

### 14.5 T-2 to T-0 min: Final GO/NO-GO
- Initial live allocation confirmed: **$100**
- Risk caps reviewed
- Kill-switch tested
- Incident/log path confirmed

Decision: GO / NO-GO

### 14.6 Post-Launch (First 30 Minutes)
- Monitor audit output
- Do not increase size
- If abnormal: kill switch, stop risk, capture logs, reconcile
