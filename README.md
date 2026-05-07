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
- `examples/run_demo.py`: Demo flow with simulated market data and dry-run execution.

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

## Important

This code is educational infrastructure and not investment advice. Validate legal, tax, and regulatory obligations before live use.
