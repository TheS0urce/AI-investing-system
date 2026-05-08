# AI Investing System Operational Runbook

## 1) Purpose and safety model

This runbook defines how to safely operate, monitor, and scale this system.

Core operating principles:
- **Capital preservation first**.
- **Fail closed**: if data/API/risk checks fail, no new risk is opened.
- **Human approval default** for risky actions.
- **Earn-the-right-to-scale**: capital scaling only after clean, repeatable performance windows.

---

## 2) Required setup checklist

Before first live run, complete all items:

### 2.1 Legal, compliance, and account prerequisites
- Confirm your jurisdiction allows your intended assets and automation mode.
- Confirm tax obligations and reporting requirements.
- Confirm broker API terms allow algorithmic order placement.

### 2.2 Financial account setup (bank + broker)
1. Create a **dedicated bank account** for strategy funding and withdrawals (avoid mixing household cash flows).
2. Open a **broker account** with API support.
3. Link bank account to broker and verify micro-deposits/transfers.
4. Enable 2FA on bank + broker + email.
5. Create API keys with least privilege:
   - Start with **read-only** while testing.
   - Enable trading permissions only after simulation and dry-run validation.
6. Define transfer controls:
   - Max single top-up amount.
   - Max weekly transfer amount.
   - Manual dual-check before adding capital.

> Never store bank credentials in this repo. Use broker API keys and environment secrets only.

### 2.3 Infrastructure setup
- Mac mini online and stable power/network.
- Python virtual environment created.
- Dependencies installed.
- LaunchAgent configured for persistent service.
- Logs directory configured.

### 2.4 Security setup
- `.env` created locally with strong API key(s).
- `.env` excluded from git.
- Tailscale (or equivalent private network) configured for remote iPhone access.
- No public router port-forwarding.

---

## 3) Configuration baseline

Use conservative defaults for small accounts:
- Max position size: <= 5% equity.
- Max daily realized loss: <= 2% equity.
- Max rolling/window drawdown: <= 8%.
- Keep reserve outside strategy: >= 30% of total equity.

If any threshold is breached:
1. Stop opening new positions.
2. Reduce exposure.
3. Send alert.
4. Require human review before resume.

---

## 4) Startup procedures

## 4.1 First-time bootstrap
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Create `.env` (example):
```env
AI_API_KEY=<long-random-secret>
AI_RATE_LIMIT_PER_MINUTE=60
```

## 4.2 Start local service
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## 4.3 Start persistent service (launchd)
Use your configured LaunchAgent and verify:
```bash
launchctl list | grep com.aiinvesting.api
curl -s http://127.0.0.1:8000/health
```

---

## 5) Pre-trade daily checklist

Run before market session:
1. `git status` clean.
2. Health endpoint returns OK.
3. Auth checks pass:
   - `/simulate_tick` without key => 401
   - with key => 200
4. Latest tests pass.
5. No critical errors in logs.
6. Broker connectivity confirmed.
7. Kill switch state confirmed OFF unless intentionally paused.

---

## 6) Testing gates (anti-drift / anti-walkabout / anti-debt)

Mandatory before any deploy:
```bash
./scripts/check.sh
```

And/or explicitly:
```bash
pytest -q --cov=src/ai_investing --cov-report=term-missing
python examples/run_demo.py
```

Do not deploy if:
- Any test fails.
- Coverage drops on safety-critical modules.
- Unauthorized endpoint behavior regresses.

---

## 7) Monitoring and alerting

Monitor these continuously:
- Service health (HTTP 200 on `/health`).
- Error logs growth rate.
- Count of blocked orders by reason.
- Kill-switch activations.
- API failure/data gap counts.

Minimum alerts:
- Service down.
- Daily loss threshold breach.
- Drawdown threshold breach.
- Repeated API/data failures.

---

## 8) Incident response playbook

If safety breach or abnormal behavior:
1. Activate kill switch / pause strategy.
2. Stop new orders.
3. Snapshot logs and recent events.
4. Reconcile positions with broker.
5. Perform root-cause analysis.
6. Resume only after tests + human sign-off.

If repeated failure windows >= 2: keep paused until remediation and successful review window.

---

## 9) High-level profit-scaling algorithm integration

Use scaling logic to adjust *allowed strategy capital*, not directional aggression.

### Inputs
- `starting_capital = 50`
- `reserve_ratio_min = 0.30`
- `review_window_days = 30`
- `max_strategy_allocation_pct = 0.70`
- `max_position_size_pct = 0.05`
- `max_daily_loss_pct = 0.02`
- `max_window_drawdown_pct = 0.08`
- `max_external_addition_per_review = 50`

### Window evaluation logic
At each review window:
- Compute `equity = cash + invested_value`
- Compute `realised_profit = closed_pnl_after_fees`
- Compute `profit_margin = realised_profit / starting_equity_of_window`
- Determine `ops_ok = no_critical_api_errors AND no_data_gaps AND no_kill_switch_events`

If `not ops_ok` OR drawdown breach:
- `allow_new_external_capital = 0`
- `reinvest_fraction_of_profit = 0`
- Move all new profit to reserve
- Reduce risk budget
- Pause strategy after repeated failure windows

Else scale conservatively by profit band:
- `< 0`: no reinvestment, no top-up
- `< 0.05`: reinvest 25%, allow top-up `min(10% equity, 50)`
- `< 0.15`: reinvest 40%, allow top-up `min(20% equity, 50)`
- `>= 0.15`: reinvest 60%, allow top-up `min(30% equity, 50)`

Then cap strategy capital:
- `strategy_capital <= equity * max_strategy_allocation_pct`

Always enforce hard limits:
- Per-position <= 5% equity
- Daily realized loss <= 2% equity
- Breach => stop opening new trades + reduce exposure + alert

### Operational interpretation
The system must **earn the right to scale** through clean, repeatable windows with low operational error. Reserve capital remains outside strategy blast radius.

---

## 10) Suggested implementation hook points

- Add a `scaling.py` module with pure functions for window evaluation.
- Persist window metrics (PnL, drawdown, ops events) in durable storage.
- Apply scaling output to risk config prior to each new window.
- Include unit tests for every branch in scaling logic.

---

## 11) iPhone access runbook

1. Ensure service healthy on Mac mini.
2. Connect iPhone and Mac mini to Tailscale.
3. Access via Tailscale IP/DNS:
   - `http://<tailscale-ip>:8000/health`
4. Use API key for protected endpoints.
5. If unreachable:
   - Check Tailscale connected on both devices.
   - Check service listening on 8000.
   - Check local firewall permissions.

---

## 12) Change management and release

For each change:
1. Create branch.
2. Implement with tests.
3. Run check script.
4. Review diff for secrets/artifacts.
5. Merge only when green.
6. Post-deploy smoke test (`/health`, auth checks, demo path).

Rollback trigger: any failed smoke test or unexpected order behavior.

## Weekly Operations Checklist (Production Safety Rhythm)

### 1) Repo and release hygiene
- [ ] `git switch main && git pull origin main`
- [ ] `git status` is clean
- [ ] Confirm current deployed commit/tag matches expected release

### 2) Safety + drift checks
- [ ] Run `./scripts/check.sh`
- [ ] Confirm tests pass and no unexpected coverage drops
- [ ] Run demo smoke check: `python examples/run_demo.py`
- [ ] Verify expected safety blocking behavior still appears when edge is insufficient

### 3) API security checks
- [ ] `/health` returns 200
- [ ] `/simulate_tick` without API key returns 401
- [ ] `/simulate_tick` with valid API key returns 200
- [ ] Confirm `.env` is not tracked in git (`git ls-files | grep .env` returns nothing)

### 4) Runtime health checks
- [ ] LaunchAgent service is running (`launchctl list | grep com.aiinvesting.api`)
- [ ] Review `logs/api.err.log` for repeated failures
- [ ] Review `logs/api.out.log` for unexpected spikes in blocked reasons
- [ ] Confirm no sustained restart loops or watchdog incidents

### 5) Risk and capital controls
- [ ] Confirm kill switch state is as intended
- [ ] Review daily loss and drawdown metrics
- [ ] Confirm reserve ratio is maintained per policy
- [ ] Confirm no unauthorized parameter drift in risk config

### 6) Secrets and access
- [ ] Verify API key age (rotate if due)
- [ ] Verify Tailscale devices are only expected/trusted devices
- [ ] Confirm no public port-forwarding enabled on router
- [ ] Confirm MFA remains enabled on broker/bank/email

### 7) Backup and recovery
- [ ] Verify latest backup exists and is readable
- [ ] Run a quick restore sanity test (quarterly full restore drill)
- [ ] Confirm incident response contact/checklist is current

### 8) Change management
- [ ] Any production change had passing tests + peer review
- [ ] Post-deploy smoke checks were completed and logged
- [ ] Record weekly ops summary (issues, actions, next risks)

---

### Command Pack (copy/paste)
```bash
git switch main && git pull origin main
git status
./scripts/check.sh
curl -s http://127.0.0.1:8000/health
curl -i -X POST http://127.0.0.1:8000/simulate_tick -H "Content-Type: application/json" -d '{}'
source .env && curl -s -X POST http://127.0.0.1:8000/simulate_tick -H "Content-Type: application/json" -H "X-API-Key: $AI_API_KEY" -d '{}'
launchctl list | grep com.aiinvesting.api

## Monthly Governance Checklist (Risk, Scaling, Security, Resilience)

### 1) Security governance
- [ ] Rotate API key (or confirm age < 90 days)
- [ ] Verify `.env` remains untracked and local-only
- [ ] Review Tailscale device list; remove unknown/stale devices
- [ ] Verify MFA still enabled for broker, bank, email, and GitHub
- [ ] Confirm no public router port-forwarding exists

### 2) Strategy risk governance
- [ ] Review 30-day realized PnL after fees
- [ ] Review 30-day max drawdown
- [ ] Review daily loss breach count
- [ ] Review kill-switch activations and reasons
- [ ] Review blocked order reason distribution (risk/value sanity)

### 3) Profit-scaling review window decision (30-day cadence)
Inputs:
- starting equity of window
- realized profit after fees
- window drawdown
- ops status (critical API errors / data gaps / kill-switch events)

Decision policy:
- If `ops not clean` OR drawdown breach:
  - no new external capital
  - no profit reinvestment
  - move profit to reserve
  - reduce risk budget
  - if repeated failure windows >= 2, keep strategy paused
- If clean + profitable:
  - apply reinvest/top-up bands per scaling policy
  - enforce strategy allocation cap
  - preserve minimum reserve ratio

Checklist:
- [ ] `ops_ok` evaluated and documented
- [ ] `profit_margin` computed and documented
- [ ] `reinvest_fraction` decision documented
- [ ] `external_addition_limit` decision documented
- [ ] `strategy_capital` cap enforcement confirmed
- [ ] reserve ratio still >= policy minimum

### 4) Operational resilience
- [ ] Run full quality gate (`./scripts/check.sh`)
- [ ] Confirm CI workflow green on latest default branch
- [ ] Validate launch service auto-restart behavior (controlled restart test)
- [ ] Review error logs for recurring patterns
- [ ] Confirm monitoring/alerts still deliver notifications

### 5) Backup and disaster recovery
- [ ] Verify latest backup timestamp and integrity
- [ ] Restore drill in clean environment (monthly lightweight / quarterly full)
- [ ] Verify restore can:
  - run tests
  - start API
  - pass auth smoke checks

### 6) Incident drill cadence
- [ ] Run a tabletop incident drill this month:
  - scenario: bad data feed / auth failure / prolonged outage
  - verify kill-switch + pause workflow
  - verify reconciliation + resume checklist
- [ ] Capture lessons learned and update runbook

### 7) Compliance & financial controls
- [ ] Reconcile broker statements vs internal logs
- [ ] Reconcile bank transfers and reserve balances
- [ ] Confirm no unauthorized transfer or API permission changes
- [ ] Confirm tax record exports are archived

### 8) Governance sign-off
- [ ] Monthly review completed by operator
- [ ] Open action items tracked with owner + due date
- [ ] “Safe to continue operation” decision recorded