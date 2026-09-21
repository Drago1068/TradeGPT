from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class LeaderRelationship:
    """Context overlay used after base scoring to compare related movers.

    The overlay never bypasses data/risk gates. It exists to prevent a strong
    headline candidate from automatically outranking an accelerating peer or
    second-wave name simply because its catalyst is easier to explain.
    """

    group: str
    role: str  # LEADER, EMERGING_LEADER, SECOND_WAVE, SYMPATHY
    peer_confirmation: float = 0.0
    acceleration: float = 0.0
    relative_strength: float = 0.0
    catalyst_freshness: float = 0.0

    def __post_init__(self) -> None:
        if self.role not in {"LEADER", "EMERGING_LEADER", "SECOND_WAVE", "SYMPATHY"}:
            raise ValueError("invalid leader-ladder role")
        values = (
            self.peer_confirmation,
            self.acceleration,
            self.relative_strength,
            self.catalyst_freshness,
        )
        if any(value < 0 or value > 100 for value in values):
            raise ValueError("leader-ladder evidence must be between 0 and 100")


def relationship_adjustment(
    relationship: LeaderRelationship,
    *,
    max_adjustment: float = 8.0,
) -> float:
    """Return a bounded context adjustment; zero means no context advantage."""

    if max_adjustment < 0:
        raise ValueError("max_adjustment must be non-negative")

    signal = (
        relationship.peer_confirmation * 0.30
        + relationship.acceleration * 0.30
        + relationship.relative_strength * 0.25
        + relationship.catalyst_freshness * 0.15
    )
    role_bonus = {
        "LEADER": 0.0,
        "EMERGING_LEADER": 1.0,
        "SECOND_WAVE": 0.5,
        "SYMPATHY": 0.0,
    }[relationship.role]
    # Center at 50 so the overlay rewards evidence above neutral and penalizes
    # weak confirmation without replacing the underlying deterministic score.
    adjustment = ((signal - 50.0) / 50.0) * max_adjustment + role_bonus
    return round(max(-max_adjustment, min(max_adjustment, adjustment)), 2)


def rank_with_leader_ladder(
    candidates: Iterable[tuple[str, float]],
    relationships: Mapping[str, LeaderRelationship],
    *,
    limit: int = 3,
    max_adjustment: float = 8.0,
) -> tuple[tuple[str, float, float], ...]:
    """Rank candidates using base score plus a bounded market-context overlay.

    Returns (symbol, adjusted_score, adjustment). Base scores remain visible so
    the post-mortem can distinguish raw qualification from context competition.
    """

    if limit < 1:
        raise ValueError("limit must be >= 1")

    ranked = []
    for symbol, base_score in candidates:
        relationship = relationships.get(symbol)
        adjustment = (
            relationship_adjustment(relationship, max_adjustment=max_adjustment)
            if relationship is not None
            else 0.0
        )
        ranked.append((symbol, round(base_score + adjustment, 2), adjustment))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return tuple(ranked[:limit])
