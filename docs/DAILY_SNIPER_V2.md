# TradeGPT Daily Sniper V2

The 08:00 ET scan is now a wide discovery funnel followed by strict qualification. It may return zero, one, two, or three A+ candidates; it must never pad the Top-3.

## Discovery funnel

Search broadly across fresh earnings/guidance, FDA/clinical, contracts/orders, M&A, regulatory events, analyst actions, product/customer news, sector catalysts, abnormal volume, relative strength, and pre-breakout compression. Small caps are eligible, subject to liquidity and execution gates.

## Required qualification

Every candidate should record:
- Catalyst verified and whether it explains the move.
- Abnormal/relative volume and dollar volume.
- Volume quality: whether participation produces price acceptance rather than rejection/churn.
- Relative strength vs SPY/QQQ, sector, and peers when available.
- Price structure and pre-breakout behavior.
- Trade location: distance to VWAP, support/resistance, and extension risk.
- Liquidity/execution quality.
- Market/sector regime fit.
- Gap quality and extension penalty.
- Expected reward/risk, with 2.0R minimum and 2.5R preferred.

## Score

Weighted score emphasizes catalyst quality (20%), abnormal volume (10%), relative strength (10%), sector relative strength (5%), price structure (15%), trade location (15%), liquidity (10%), regime fit (5%), pre-breakout (5%), gap quality (2.5%), and volume quality (2.5%). Extended candidates receive a penalty.

## Hard gates

A candidate cannot qualify as A+ unless data is verified, the catalyst is verified and explains the move, catalyst quality >=70, price structure >=70, trade location >=70, liquidity >=60, volume quality >=50, and expected reward/risk >=2.0.

## Execution states

- DISCOVERED: found in broad funnel.
- WATCH: promising but incomplete.
- ARMED: all preconditions except trigger are present.
- TRIGGERED: live trigger confirmed.
- TRADE_READY: execution and risk gates passed.
- ENTER: actual user/broker action, if separately authorized.
- INVALIDATED/REJECTED: hard gate failed.

A+ is a qualification band, not permission to enter. Missing live data remains DATA NOT VERIFIED.

## Measurement loop

Each candidate should be retained for later outcome measurement: discovery timestamp/price, trigger, stop, targets, MFE, MAE, trigger occurrence/time, T1/T2/T3 attainment, stop outcome, realized R, and failure reason. The 10:15 and 12:30 scans should update the same candidate lineage where applicable. This enables forward evaluation rather than subjective tuning.
