from __future__ import annotations

from dataclasses import dataclass

from .models import Candidate


@dataclass(frozen=True)
class ScorePolicy:
    a_plus_min: float = 90.0
    armed_min: float = 82.0
    watch_min: float = 74.0
    discovery_min: float = 65.0


def composite_score(
    *, catalyst: float, technical: float, relative_strength: float, liquidity: float
) -> float:
    """Return the deterministic weighted score, bounded to 0..100."""
    values = (catalyst, technical, relative_strength, liquidity)
    if any(v < 0 or v > 100 for v in values):
        raise ValueError("score components must be between 0 and 100")
    return round(
        catalyst * 0.30
        + technical * 0.30
        + relative_strength * 0.20
        + liquidity * 0.20,
        2,
    )


def score_band(score: float, policy: ScorePolicy | None = None) -> str:
    p = policy or ScorePolicy()
    if score >= p.a_plus_min:
        return "A+"
    if score >= p.armed_min:
        return "A"
    if score >= p.watch_min:
        return "WATCH"
    if score >= p.discovery_min:
        return "DISCOVERY"
    return "PASS"


def execution_gate(candidate: Candidate, *, policy: ScorePolicy | None = None) -> tuple[bool, tuple[str, ...]]:
    """Hard execution gate: score never overrides missing data or invalid trade geometry."""
    p = policy or ScorePolicy()
    reasons: list[str] = []
    if not candidate.data_verified:
        reasons.append("DATA_NOT_VERIFIED")
    if candidate.score < p.a_plus_min:
        reasons.append("SCORE_BELOW_A_PLUS")
    if candidate.entry_trigger is None:
        reasons.append("NO_ENTRY_TRIGGER")
    if candidate.stop_price is None:
        reasons.append("NO_STOP")
    if candidate.target_price is None:
        reasons.append("NO_TARGET")
    if candidate.last_price is not None and candidate.entry_trigger is not None:
        if candidate.last_price > candidate.entry_trigger:
            reasons.append("CHASE_GUARD")
    if candidate.stop_price is not None and candidate.entry_trigger is not None:
        if candidate.stop_price >= candidate.entry_trigger:
            reasons.append("INVALID_STOP")
    if candidate.target_price is not None and candidate.entry_trigger is not None:
        if candidate.target_price <= candidate.entry_trigger:
            reasons.append("INVALID_TARGET")
    if candidate.target_price is not None and candidate.entry_trigger is not None and candidate.stop_price is not None:
        risk = candidate.entry_trigger - candidate.stop_price
        reward = candidate.target_price - candidate.entry_trigger
        if risk <= 0 or reward / risk < 2.0:
            reasons.append("REWARD_RISK_GATE")
    return not reasons, tuple(reasons)
