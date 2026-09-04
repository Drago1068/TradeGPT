from __future__ import annotations

from dataclasses import dataclass

from .models import RiskDecision


@dataclass(frozen=True)
class RiskPolicy:
    max_trade_risk_pct: float = 0.01
    exceptional_trade_risk_pct: float = 0.02
    max_portfolio_heat_pct: float = 0.05
    daily_loss_limit_pct: float = 0.03
    min_reward_risk: float = 2.0
    min_price: float = 3.0
    min_adv_shares: int = 500_000
    min_adv_dollars: float = 5_000_000


def evaluate_trade(
    *,
    equity: float,
    entry: float,
    stop: float,
    target: float,
    current_heat: float = 0.0,
    daily_loss: float = 0.0,
    adv_shares: int | None = None,
    adv_dollars: float | None = None,
    data_verified: bool = False,
    exceptional: bool = False,
    policy: RiskPolicy | None = None,
) -> RiskDecision:
    p = policy or RiskPolicy()
    reasons: list[str] = []
    if equity <= 0:
        reasons.append("INVALID_EQUITY")
    if entry <= 0 or stop <= 0 or target <= 0:
        reasons.append("INVALID_PRICES")
    if stop >= entry:
        reasons.append("STOP_NOT_BELOW_ENTRY")
    if target <= entry:
        reasons.append("TARGET_NOT_ABOVE_ENTRY")
    if not data_verified:
        reasons.append("DATA_NOT_VERIFIED")
    if entry < p.min_price:
        reasons.append("PRICE_BELOW_GATE")
    if adv_shares is None or adv_shares < p.min_adv_shares:
        reasons.append("SHARE_LIQUIDITY_GATE")
    if adv_dollars is None or adv_dollars < p.min_adv_dollars:
        reasons.append("DOLLAR_LIQUIDITY_GATE")
    if daily_loss >= equity * p.daily_loss_limit_pct:
        reasons.append("DAILY_LOSS_LIMIT")

    per_share_risk = entry - stop
    reward_risk = ((target - entry) / per_share_risk) if per_share_risk > 0 else None
    if reward_risk is None or reward_risk < p.min_reward_risk:
        reasons.append("REWARD_RISK_GATE")

    allowed_risk = equity * (p.exceptional_trade_risk_pct if exceptional else p.max_trade_risk_pct)
    remaining_heat = equity * p.max_portfolio_heat_pct - current_heat
    risk_budget = min(allowed_risk, max(0.0, remaining_heat))
    shares = int(risk_budget // per_share_risk) if per_share_risk > 0 else 0
    risk_dollars = shares * per_share_risk
    if shares < 1:
        reasons.append("NO_VALID_POSITION_SIZE")

    return RiskDecision(
        approved=not reasons,
        shares=shares if not reasons else 0,
        risk_dollars=risk_dollars if not reasons else 0.0,
        reward_risk=reward_risk,
        reasons=tuple(reasons),
    )
