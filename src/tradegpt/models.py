from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CandidateState(str, Enum):
    DISCOVERED = "DISCOVERED"
    WATCH = "WATCH"
    ARMED = "ARMED"
    TRIGGERED = "TRIGGERED"
    TRADE_READY = "TRADE_READY"
    ENTERED = "ENTERED"
    MANAGE = "MANAGE"
    EXITED = "EXITED"
    INVALIDATED = "INVALIDATED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    timestamp: datetime
    price: Optional[float]
    vwap: Optional[float] = None
    rvol: Optional[float] = None
    relative_strength: Optional[float] = None
    data_verified: bool = False


@dataclass
class Candidate:
    symbol: str
    discovered_at: datetime
    state: CandidateState = CandidateState.DISCOVERED
    score: float = 0.0
    catalyst_score: float = 0.0
    technical_score: float = 0.0
    relative_strength_score: float = 0.0
    liquidity_score: float = 0.0
    entry_trigger: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    last_price: Optional[float] = None
    data_verified: bool = False
    rejection_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    shares: int
    risk_dollars: float
    reward_risk: Optional[float]
    reasons: tuple[str, ...] = ()
