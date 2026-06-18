# AI Investing System (Safety-First)

This repository contains a **self-built AI investing system** designed for retail constraints and safety-first operation.

## Core principles

1. **Capital preservation first**: strict drawdown, position, and leverage limits.
2. **Regulatory and policy gating**: no execution if controls fail.
3. **Human-in-the-loop by default**: autonomous mode is optional and constrained.
4. **Deterministic guardrails around probabilistic models**.
5. **Cost-aware for small accounts**: blocks strategies where fees/slippage dominate edge.

## Architecture

- `src/ai_investing/config.py`: Typed configuration for broker, risk, and policy limits.
- `src/ai_investing/models.py`: Domain models and order lifecycle entities.
- `src/ai_investing/safety.py`: Safety engine and hard pre-trade checks.
- `src/ai_investing/strategy.py`: Signal generation interface and sample model strategy.
- `src/ai_investing/execution.py`: Execution planner with slippage/fee-aware sizing.
- `src/ai_investing/system.py`: End-to-end orchestrator with audit logs and fail-closed behavior.
- `src/ai_investing/alpaca.py`: Alpaca paper-only adapter and read-only market/account helpers.
- `src/ai_investing/preauthorization.py`: Expiring paper authorization, bounded risk, and performance progression.
- `examples/run_demo.py`: Demo flow with simulated market data and dry-run execution.
- `dashboard.py`: Local Streamlit operator dashboard.

## Safety features implemented

- Account-level max daily loss and max peak-to-trough drawdown stop.
- Per-symbol exposure, gross exposure, and order notional caps.
- Optional leverage hard cap (default 1.0 for cash-only).
- Cooldown after consecutive losses.
- Liquidity/volatility sanity filters (no trades on bad ticks).
- Fee + slippage viability check (blocks negative expectancy net of costs).
- Kill-switch conditions (manual and automatic).
- Two-phase execution: proposal -> safety review -> approval -> execution.
- Immutable audit events with reason codes for every blocked action.
- Fail-closed defaults (missing data/config denies trading).

## Clarification questions to avoid drift/ghosting

Before live deployment, answer these:

1. What broker + asset universe (US equities, ETFs, crypto, options)?
2. Is this **advisory-only** or should it place live orders?
3. Required regulatory constraints (PDT, accredited-only products, jurisdiction)?
4. Account size and max tolerated monthly drawdown?
5. Should autonomous mode ever bypass manual approval? (default: no)
6. Preferred strategy family (long-only momentum, mean reversion, factor rotation)?
7. Data budget and latency requirements?

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python examples/run_demo.py
```

## Current Paper-Trading Stage

The current deployment stage is **Alpaca paper trading only**:

- Broker mode: `paper`
- Live routing: disabled
- Autonomous execution: disabled
- Manual approval: required
- Paper order submit/cancel: guarded by exact confirmation phrases
- Optional bounded paper preauthorization: inactive until explicitly activated
- Market-open watch mode: read-only by default
- Market-open watch launcher requires full `PAPER-MARKET-OPEN-GO` preflight before running

Useful local commands:

```bash
./scripts/check.sh
.venv/bin/python scripts/verify_macos_apps.py
.venv/bin/python scripts/paper_market_open_preflight.py
.venv/bin/python scripts/paper_next_action.py
.venv/bin/python scripts/scaling_policy_report.py
.venv/bin/python scripts/paper_preauthorization_replay_report.py
.venv/bin/python scripts/run_market_open_paper_watch.py --symbol QQQ --feed iex --interval-seconds 60 --iterations 30
./scripts/install_market_open_watch_agent.sh
```

Clickable Mac launchers are installed in:

```text
~/Applications/AI Investment
```

The current launcher set includes Start API, Health, Dashboard, Daily Ops, Market Preflight, Next Action, and Stop API.

For unattended market-open validation, install the local watch LaunchAgent with
`./scripts/install_market_open_watch_agent.sh`. It checks the paper clock every five
minutes, waits until at least 9:45 a.m. New York time, and runs the focused read-only
watch once per U.S. session through approximately 10:10 a.m. It does not activate
preauthorization or submit orders.

The watch runner also has an explicit paper-only submit bridge for the bounded
preauthorization endpoint:

```bash
.venv/bin/python scripts/run_market_open_paper_watch.py --preauthorized-submit
```

This mode remains off by default. It only attempts paper bracket submission when a
watch tick produces an `order_proposal`, and the API still requires an active
bounded paper authorization lease plus all paper-only broker guards.

### Bounded paper preauthorization

The preauthorization mechanism is paper-only and remains inactive by default. It does not enable
live routing or alter the existing manual order endpoint.

Initial envelope:

- 72-hour expiring authorization lease
- Long-only fractional entries in `SPY`, `QQQ`, `AAPL`, `MSFT`, and `NVDA`
- Maximum `$4` per entry, two entries per session, and `$8` gross exposure
- Hard `$2` daily realized-loss ceiling that never expands above `$2` automatically
- Capital-aware limits: 4% per entry, 8% gross exposure, and 2% daily loss
- Effective limits use the lower of the capital percentage and governed dollar cap
- Capital growth expands limits only after qualified 20-trade performance windows
- Capital declines tighten limits immediately, including the daily-loss ceiling
- The capital basis is the preauthorization ledger's current equity, updated from realized
  closed trades; Alpaca paper-account buying power is intentionally not used for sizing
- Minimum 9 bps expected edge and maximum 30 bps spread
- Attached 1.5% stop-loss and 3% take-profit bracket legs
- Automatic pause after three consecutive losses or one operational error
- 10% sizing progression after each qualified 20-trade window, capped at three steps

The status, activation, revocation, and bounded-submit routes are:

```text
GET  /broker/paper/preauthorization
POST /broker/paper/preauthorization/activate
POST /broker/paper/preauthorization/revoke
POST /broker/paper/preauthorization/submit
```

Activation requires `AUTHORIZE_BOUNDED_PAPER`; revocation requires
`REVOKE_BOUNDED_PAPER`. Broker or state errors fail closed and revoke active execution.
The fractional bracket combination must be verified in Alpaca paper trading before this route is
used unattended; a broker rejection is treated as an operational pause.

## Important

This code is educational infrastructure and not investment advice. Validate legal, tax, and regulatory obligations before live use.

---

## System Design + Risk Profile (One-Page)

### Purpose
This application is a safety-first trading decision scaffold designed for controlled operation under retail constraints. It is intended for staged rollout (simulation → paper/shadow → limited live) with human governance and deterministic guardrails.

### High-Level Architecture
The system is composed of:
- **API layer (`app.py`)**  
  Exposes:
  - `GET /health`
  - `POST /simulate_tick` (API key protected)
  - `GET /dashboard/summary` (API key protected)
  - Alpaca paper-only account, clock, readiness, strategy preview, watch, preflight, and next-action endpoints
- **Core orchestration (`src/ai_investing/system.py`)**  
  Pipeline: market checks → signal generation → order proposal → cost/edge gate → portfolio/risk gate → manual review or approval.
- **Safety/risk engine (`src/ai_investing/safety.py`)**  
  Enforces hard pre-trade controls.
- **Execution planner (`src/ai_investing/execution.py`)**  
  Converts signal conviction into order size with capped risk budget.
- **Strategy module (`src/ai_investing/strategy.py`)**  
  Placeholder volatility-adjusted momentum signal generator.
- **Scaling policy layer (`src/ai_investing/scaling.py`)**  
  Deterministic reinvestment and allocation policy helpers, with `scripts/scaling_policy_report.py` for operator review.

### Decision Flow (Per Tick)
1. Validate market input quality (price, spread, liquidity, volatility).  
2. Generate signal (or no-trade).  
3. Convert signal to order proposal if confidence threshold is met.  
4. Enforce net-edge-after-costs gate (fees + slippage).  
5. Enforce portfolio and order risk constraints.  
6. Return proposal for manual approval (default) or mark approved if policy allows.

### Checks & Balances (Risk Controls)
- **Market gates**
  - Invalid/non-positive price blocked
  - Wide spread blocked
  - Insufficient volume blocked
  - Excess volatility blocked
- **Order/portfolio gates**
  - Kill switch
  - Cooldown after consecutive losses
  - Daily loss cap
  - Drawdown cap
  - Max order notional
  - Per-symbol exposure cap
  - Gross exposure cap
  - Leverage cap
- **Cost viability gate**
  - Expected edge must remain above minimum net edge after fees/slippage

### Defaults (Safety-First)
- Manual approval required by default
- Autonomous execution disabled by default
- Kill switch available
- Fail-closed behavior when controls fail

### Strategy & Sizing Profile
- Strategy is a simple, deterministic placeholder (not production alpha).
- Execution uses a fixed risk budget (2% of equity) and conviction-weighted sizing.
- Low-confidence signals are ignored.
- No live broker routing logic is included in this scaffold.

### Self-Learning Status
- **No online self-learning loop is implemented in runtime.**
- No reinforcement updates, no automatic re-training, and no autonomous parameter adaptation.
- Evolution is intended to occur via governed code/model promotion, not unattended online drift.

### ROI / Scaling Policy Settings
- Realized profit split helper:
  - 38% reinvest
  - 62% reserve
- ROI tier allocation helper:
  - `< $500`: accumulation (low risk focus)
  - `$500–$999`: growth (medium risk bias)
  - `>= $1000`: optimized mix
- Strategy capital cap helper:
  - Max strategy allocation (% of equity)
  - Max external top-up per review window

### Operational Readiness Model
- **Local/staging preflight GO** requires:
  - checks/tests pass,
  - endpoint auth behavior verified,
  - clean git state.
- **Live-trading GO** additionally requires:
  - legal/compliance confirmation,
  - broker/API permission hardening,
  - governance and incident readiness,
  - runbook sign-off artefacts.

### Current Scope & Limitations
- Educational/safety infrastructure, not investment advice.
- Paper-only broker integration exists for staged validation; live routing remains disabled.
- Not a complete OMS/EMS or live broker-execution stack.
- Requires explicit human governance and staged rollout before any live capital deployment.
