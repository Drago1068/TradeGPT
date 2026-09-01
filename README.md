# TradeGPT V3 — Adaptive Intelligence Engine

TradeGPT V3 is an automated market-discovery and research architecture designed to eliminate manual discovery and copy/paste workflows while preserving independent model attribution, empirical benchmarking, and risk-first decision gates.

## Architecture

1. Automated quantitative/event discovery
2. Candidate Union Ledger
3. Adaptive Intelligence Layer
4. Task-specific model routing
5. Empirical model benchmarking
6. Adversarial research/audit
7. Meta Engine risk and quality gates
8. DISCOVERED → WATCH → ARMED → TRIGGERED → TRADE READY → ENTER/MANAGE → EXIT / INVALIDATED / REJECTED state machine
9. Forward-test and discovery-lead-time measurement
10. Scheduled market-session orchestration and observability

## Strategy Engines

### A — 0DTE Options
- SPY, QQQ, IWM only
- Delta > 0.60 ITM
- Primary windows: 09:45–11:30 ET and 14:00–15:30 ET
- Never hold through 15:45 ET

### B — Short-Duration Options
- 14–45 DTE
- Delta 0.50–0.70
- Prefer long options when IV Rank < 50%
- When IV Rank > 80%, prefer stock structures

### C — Stocks
- Momentum / swing
- Breakout + consolidation
- RVOL > 2.0

### D — Pre-Breakout Discovery
- 10-day price range < 5%
- ATR contracting for 5+ days
- Relative strength rising versus SPY

## Risk Controls

- Maximum account risk per trade: 1.0%
- Maximum portfolio heat: 5.0%
- Minimum reward/risk: 2.0R
- Daily loss limit: 3.0%
- Liquidity gates: price > $3, 30-day ADV > 500k shares, and 30-day ADV dollar value > $5M

## Data Integrity

Production decisions require verified market data. Missing or stale L1/L2, OPRA, index, EOD, VWAP/AVWAP, or RVOL inputs must be explicitly flagged as `DATA NOT VERIFIED` rather than silently substituted.

## Model Independence

AI models are interchangeable research workers. No specific model—including Qwen—is a required architectural dependency. Models are evaluated by task and observed forward performance rather than arbitrary preference.

## Development Status

Phase 1 foundation is initialized. The next implementation layer establishes repository structure, configuration, schemas, deterministic risk gates, scan orchestration, model registry/router interfaces, and automated acceptance tests before live execution is enabled.

## Safety

TradeGPT is research and decision-support software. It does not guarantee returns and must not bypass data verification, liquidity, position sizing, reward/risk, portfolio-risk, or execution gates.
