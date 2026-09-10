from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class SniperEvidence:
    """Evidence for discovery, qualification, and audit of a sniper candidate."""

    symbol: str
    catalyst_quality: float
    catalyst_verified: bool
    catalyst_explains_move: bool
    abnormal_volume: float
    dollar_volume: float
    relative_strength: float
    sector_relative_strength: float
    price_structure: float
    trade_location: float
    liquidity: float
    regime_fit: float
    reward_risk: float
    pre_breakout: float = 0.0
    gap_quality: float = 0.0
    volume_quality: float = 0.0
    extended: bool = False
    data_verified: bool = False
    rejection_reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SniperPolicy:
    """Policy for the 8:00 ET discovery funnel; never pads the Top-3."""

    a_plus_min: float = 85.0
    min_catalyst_quality: float = 70.0
    min_price_structure: float = 70.0
    min_trade_location: float = 70.0
    min_liquidity: float = 60.0
    min_reward_risk: float = 2.0
    min_volume_quality: float = 50.0


def sniper_score(e: SniperEvidence) -> float:
    """Score information shock, participation, relative strength, and trade location."""
    values = (
        e.catalyst_quality, e.abnormal_volume, e.relative_strength,
        e.sector_relative_strength, e.price_structure, e.trade_location,
        e.liquidity, e.regime_fit, e.pre_breakout, e.gap_quality,
        e.volume_quality,
    )
    if any(v < 0 or v > 100 for v in values):
        raise ValueError("sniper evidence scores must be between 0 and 100")
    score = (
        e.catalyst_quality * 0.20
        + e.abnormal_volume * 0.10
        + e.relative_strength * 0.10
        + e.sector_relative_strength * 0.05
        + e.price_structure * 0.15
        + e.trade_location * 0.15
        + e.liquidity * 0.10
        + e.regime_fit * 0.05
        + e.pre_breakout * 0.05
        + e.gap_quality * 0.025
        + e.volume_quality * 0.025
    )
    if e.extended:
        score -= 10.0
    return round(max(0.0, min(100.0, score)), 2)


def sniper_gate(e: SniperEvidence, *, policy: SniperPolicy | None = None) -> tuple[bool, tuple[str, ...]]:
    """Hard gates prevent headlines or momentum alone from becoming a trade."""
    p = policy or SniperPolicy()
    reasons = list(e.rejection_reasons)
    if not e.data_verified:
        reasons.append("DATA_NOT_VERIFIED")
    if not e.catalyst_verified:
        reasons.append("CATALYST_NOT_VERIFIED")
    if not e.catalyst_explains_move:
        reasons.append("MOVE_NOT_EXPLAINED_BY_CATALYST")
    if e.catalyst_quality < p.min_catalyst_quality:
        reasons.append("CATALYST_QUALITY_BELOW_FLOOR")
    if e.price_structure < p.min_price_structure:
        reasons.append("PRICE_STRUCTURE_BELOW_FLOOR")
    if e.trade_location < p.min_trade_location:
        reasons.append("TRADE_LOCATION_BELOW_FLOOR")
    if e.liquidity < p.min_liquidity:
        reasons.append("LIQUIDITY_BELOW_FLOOR")
    if e.volume_quality < p.min_volume_quality:
        reasons.append("VOLUME_QUALITY_BELOW_FLOOR")
    if e.reward_risk < p.min_reward_risk:
        reasons.append("REWARD_RISK_BELOW_FLOOR")
    return not reasons, tuple(dict.fromkeys(reasons))


def rank_sniper_candidates(
    candidates: Iterable[SniperEvidence], *, policy: SniperPolicy | None = None, limit: int = 3
) -> tuple[tuple[SniperEvidence, float], ...]:
    """Return up to limit qualified A+ candidates; never manufacture a third slot."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    p = policy or SniperPolicy()
    ranked: list[tuple[SniperEvidence, float]] = []
    for candidate in candidates:
        score = sniper_score(candidate)
        gated, _ = sniper_gate(candidate, policy=p)
        if gated and score >= p.a_plus_min:
            ranked.append((candidate, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return tuple(ranked[:limit])
