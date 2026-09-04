# Trade GPT V2 — Risk Policy

## Objective

Risk controls protect the account from model error, data error, execution error, concentration, and adverse market conditions.

## Equity

Account equity is a runtime configuration value. It must never be hard-coded into business logic.

## Default Limits

- Normal max planned risk/trade: 1.0% of equity
- Exceptional max planned risk/trade: 2.0%, explicitly enabled only
- Max portfolio heat: 5.0%
- Daily loss limit: 3.0%
- Minimum execution reward/risk: 2.0R

## Position Sizing

For stock trades:

position_size = floor(planned_risk_dollars / abs(entry_price - stop_price))

Then constrain by:
- buying power
- liquidity
- configured maximum position notional
- portfolio heat
- available shares/market constraints

If position size is zero, the trade is rejected.

## Risk Snapshot

Every TRADE READY recommendation must store:
- equity used
- planned dollar risk
- risk percentage
- entry
- stop
- stop distance
- target(s)
- expected reward
- R:R
- position size
- estimated notional
- portfolio heat before and after
- timestamp

## Stop Discipline

Stops are defined from market structure or another explicit strategy rule. The system must never widen a stop to make a rejected trade pass.

## Chasing

A trigger can become invalid for execution if the current price has moved beyond the configured maximum entry extension. A candidate may remain valid for research while being rejected for execution.

## Daily Loss Lock

When realized and configured intraday losses reach the daily loss limit, new risk-taking recommendations must be blocked until the next eligible session unless explicitly overridden by an authorized administrative control.

## Portfolio Heat

The sum of planned open-position risk must not exceed the configured portfolio heat limit.

## No Averaging Down

The initial production system does not support averaging down. Any future pyramiding feature must be separately designed and risk-budgeted.

## Options

Options are not the primary execution path in V2. Any future options module must calculate maximum planned loss using contract economics and must apply separate liquidity and volatility gates. 0DTE remains outside initial production scope.

## Safety Boundary

Risk policy is a hard gate. AI-generated confidence, score, narrative, or urgency cannot override a failed deterministic risk constraint.
