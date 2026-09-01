"""Deterministic, fail-closed risk gates for TradeGPT V3."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_trade_risk_pct: float = 0.01
    max_portfolio_heat_pct: float = 0.05
    min_reward_risk: float = 2.0
    daily_loss_limit_pct: float = 0.03
    min_price: float = 3.0
    min_adv_shares: int = 500_000
    min_adv_dollars: float = 5_000_000.0


@dataclass(frozen=True)
class RiskInput:
    equity: float
    entry: float
    stop: float
    target: float
    adv_shares: int
    adv_dollars: float
    portfolio_heat_pct: float = 0.0
    daily_loss_pct: float = 0.0
    data_verified: bool = False


def evaluate(inp: RiskInput, limits: RiskLimits = RiskLimits()) -> tuple[bool, list[str]]:
    """Return (approved, reasons). Never approve on missing/invalid data."""
    reasons: list[str] = []
    if not inp.data_verified:
        reasons.append("DATA NOT VERIFIED")
    if inp.equity <= 0:
        reasons.append("invalid equity")
    if inp.entry <= limits.min_price:
        reasons.append("price below liquidity gate")
    if inp.stop >= inp.entry:
        reasons.append("stop must be below entry")
    if inp.target <= inp.entry:
        reasons.append("target must exceed entry")
    if inp.adv_shares < limits.min_adv_shares:
        reasons.append("share liquidity gate failed")
    if inp.adv_dollars < limits.min_adv_dollars:
        reasons.append("dollar liquidity gate failed")
    if inp.portfolio_heat_pct > limits.max_portfolio_heat_pct:
        reasons.append("portfolio heat exceeded")
    if inp.daily_loss_pct >= limits.daily_loss_limit_pct:
        reasons.append("daily loss limit reached")

    if inp.stop < inp.entry and inp.target > inp.entry:
        risk = inp.entry - inp.stop
        reward = inp.target - inp.entry
        if reward / risk < limits.min_reward_risk:
            reasons.append("reward/risk below minimum")

    return (len(reasons) == 0, reasons)
