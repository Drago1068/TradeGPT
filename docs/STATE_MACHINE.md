# Trade GPT V2 — Candidate State Machine

## Purpose

The state machine separates discovery from execution and prevents promising candidates from disappearing between scans.

## States

### DISCOVERED
Candidate has passed basic discovery filters and has enough data to be tracked. No expectation of entry.

### WATCH
Candidate has meaningful setup quality but lacks one or more conditions for ARMED status.

### ARMED
Candidate has a defined thesis, trigger, invalidation, target structure, liquidity assessment, and data confidence sufficient for active monitoring.

### TRIGGERED
Objective trigger has occurred. The system must immediately re-evaluate chase, spread/liquidity, event risk, data freshness, stop distance, position sizing, and reward/risk.

### TRADE READY
All hard execution gates pass. This is the only state eligible to generate BUY NOW.

### ENTER
An entry is recorded. The system freezes the original trade plan and starts active management.

### MANAGE
Position is monitored against the immutable plan. Stop widening and unauthorized averaging down are prohibited.

### EXIT/CLOSED
Position is closed and all realized outcome metrics are recorded.

## Terminal States

### INVALIDATED
The original thesis or trigger condition is no longer valid.

### REJECTED
A hard gate failed. Rejection reason is mandatory.

### EXPIRED
Candidate remained relevant long enough to become stale without triggering.

## Required Transition Record

Every transition must record:
- candidate ID
- previous state
- new state
- timestamp in ET and UTC
- actor/system component
- trigger/reason code
- relevant price
- data-confidence snapshot
- score snapshot
- notes

## Hard Execution Gates

A candidate cannot enter TRADE READY if any of these fail:
- Required market data unavailable or stale
- Liquidity unacceptable for intended position
- Entry is chased beyond configured maximum extension
- Stop cannot be defined objectively
- Reward/risk < configured minimum
- Planned risk exceeds per-trade limit
- Portfolio heat would exceed limit
- Daily loss limit blocks new risk
- Material event risk violates configured policy
- Position size rounds below one share
- Market/session condition makes the strategy invalid

## Discovery Does Not Require Execution Eligibility

Candidates may remain DISCOVERED, WATCH, or ARMED even when they are not yet executable. This is intentional and is the primary correction to the prior over-filtered architecture.
