# Trade GPT V2 — Trading Charter

## Mission

Build a stock-first research and decision-support system designed to identify asymmetric opportunities early, qualify them objectively, control risk, learn from outcomes and missed opportunities, and evolve as evidence accumulates.

## Primary Objective

Grow the trading account through disciplined stock opportunities while avoiding forced trades and uncontrolled downside. The system must optimize for process quality and risk-adjusted opportunity capture, not trade frequency.

## Operating Principles

1. Discovery is broad; execution is selective.
2. Lower the threshold for discovery, never lower the threshold for execution.
3. No forced trades.
4. No fabricated or stale market data presented as current.
5. No averaging down.
6. No widening stops to avoid a loss.
7. No chasing extended entries.
8. Every actionable recommendation must include entry, invalidation/stop, target(s), reward/risk, position size, and planned dollar risk.
9. Failed data, liquidity, event, trigger, or risk gates are hard blockers.
10. External AI models are research/challenge workers, not permission gates.
11. Original observations and decisions are immutable after creation; corrections are appended as new events.
12. The system must record both executed trades and qualified opportunities that were missed or rejected.

## Primary Strategy Priority

Stock strategies are the default execution path. Options are optional execution vehicles and must not control discovery. 0DTE is disabled from the initial production scope until the stock-first system has passed forward-testing and acceptance criteria.

## Account/Risk Configuration

Account equity is configurable and must be read from the active account configuration rather than hard-coded. Initial deployment target is approximately $2,905.

Default risk policy:
- Normal maximum planned risk per trade: 1.0% of current equity.
- Exceptional risk ceiling: 2.0% only when explicitly authorized by configuration and all A+ gates pass.
- Maximum portfolio heat: 5.0% of equity.
- Daily loss limit: 3.0% of equity.
- Minimum reward/risk for execution: 2.0R.
- Position size must be calculated from planned dollar risk divided by per-share stop distance and constrained by available buying power, liquidity, and portfolio heat.

## Required Candidate State Machine

DISCOVERED → WATCH → ARMED → TRIGGERED → TRADE READY → ENTER → MANAGE → EXIT/CLOSED

Alternative terminal paths:
- INVALIDATED
- REJECTED
- EXPIRED

State transitions must be deterministic, timestamped, auditable, and explainable.

## Discovery Philosophy

Discovery should surface a healthy pipeline rather than only A+ trades. Candidate sources include:
- Fresh catalysts
- Post-event continuation
- Second-day momentum
- Breakout/consolidation
- Compression/pre-breakout
- Relative-strength divergence
- Sector rotation
- Sympathy/industry moves
- VWAP/AVWAP reclaim or support
- Unusual/relative volume
- High-quality technical setups without a fresh catalyst

Discovery score bands:
- 90–100: A+ / execution eligible subject to hard gates
- 82–89: A / ARMED candidate
- 74–81: WATCH
- 65–73: DISCOVERY only
- <65: PASS

Score never overrides a hard gate.

## Data Integrity

Any decision dependent on unavailable, stale, contradictory, or unverified market data must be labeled DATA NOT VERIFIED and cannot become TRADE READY.

The system must retain source timestamp and data-confidence metadata for every decision-critical input.

## Mobile Requirement

The application must be responsive and PWA-capable. Critical monitoring and decision-support functions must work on phone and tablet. Desktop is preferred for administration, configuration, analytics, and development.

## Production Boundary

Initial versions are research and decision-support only. Broker order submission must remain disabled until separately specified, implemented, tested, and explicitly authorized.
