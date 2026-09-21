from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LateDayEvidence:
    """Explicit evidence required by the 15:00 ET late-day scan."""

    afternoon_compression: float
    vwap_reclaim_or_hold: float
    breakout_or_retest: float
    dollar_volume_acceleration: float
    closing_strength: float
    next_day_swing_quality: float
    invalidation_defined: bool
    chase_threshold_defined: bool

    def __post_init__(self) -> None:
        values = (
            self.afternoon_compression,
            self.vwap_reclaim_or_hold,
            self.breakout_or_retest,
            self.dollar_volume_acceleration,
            self.closing_strength,
            self.next_day_swing_quality,
        )
        if any(value < 0 or value > 100 for value in values):
            raise ValueError("late-day evidence scores must be between 0 and 100")


def late_day_score(evidence: LateDayEvidence) -> float:
    """Score late-day setup quality without granting execution authority."""

    score = (
        evidence.afternoon_compression * 0.15
        + evidence.vwap_reclaim_or_hold * 0.15
        + evidence.breakout_or_retest * 0.20
        + evidence.dollar_volume_acceleration * 0.15
        + evidence.closing_strength * 0.15
        + evidence.next_day_swing_quality * 0.20
    )
    return round(score, 2)


def late_day_gate(evidence: LateDayEvidence) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if not evidence.invalidation_defined:
        reasons.append("NO_INVALIDATION")
    if not evidence.chase_threshold_defined:
        reasons.append("NO_CHASE_THRESHOLD")
    return not reasons, tuple(reasons)
