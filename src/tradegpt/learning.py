from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .models import CandidateState


@dataclass(frozen=True)
class Outcome:
    symbol: str
    evaluated_at: datetime
    entry_price: Optional[float]
    exit_price: Optional[float]
    stop_price: Optional[float]
    target_price: Optional[float]
    outcome_r: Optional[float]
    max_adverse_excursion_r: Optional[float] = None
    max_favorable_excursion_r: Optional[float] = None
    result: str = "UNRESOLVED"


@dataclass
class LearningRecord:
    symbol: str
    discovered_at: datetime
    discovery_score: float
    discovery_state: CandidateState
    trigger_confirmed: bool = False
    trade_ready: bool = False
    traded: bool = False
    outcome: Optional[Outcome] = None
    missed_opportunity: bool = False
    reasons: list[str] = field(default_factory=list)


class LearningLedger:
    """Append-only in-memory forward-test ledger; persistence can be backed by DB later."""

    def __init__(self) -> None:
        self._records: list[LearningRecord] = []

    def record_discovery(
        self,
        *,
        symbol: str,
        discovered_at: datetime,
        score: float,
        state: CandidateState,
    ) -> LearningRecord:
        record = LearningRecord(
            symbol=symbol.upper(),
            discovered_at=discovered_at,
            discovery_score=score,
            discovery_state=state,
        )
        self._records.append(record)
        return record

    def mark_triggered(self, record: LearningRecord) -> None:
        record.trigger_confirmed = True

    def mark_trade_ready(self, record: LearningRecord) -> None:
        record.trade_ready = True

    def mark_traded(self, record: LearningRecord) -> None:
        record.traded = True

    def record_outcome(self, record: LearningRecord, outcome: Outcome) -> None:
        record.outcome = outcome

    def mark_missed(self, record: LearningRecord, reason: str) -> None:
        record.missed_opportunity = True
        record.reasons.append(reason)

    def all(self) -> list[LearningRecord]:
        return list(self._records)

    def summary(self) -> dict[str, float | int]:
        resolved = [r.outcome for r in self._records if r.outcome and r.outcome.outcome_r is not None]
        rs = [float(o.outcome_r) for o in resolved]
        wins = [r for r in rs if r > 0]
        losses = [r for r in rs if r < 0]
        return {
            "discoveries": len(self._records),
            "trade_ready": sum(r.trade_ready for r in self._records),
            "traded": sum(r.traded for r in self._records),
            "missed_opportunities": sum(r.missed_opportunity for r in self._records),
            "resolved_outcomes": len(rs),
            "win_rate_pct": round((len(wins) / len(rs)) * 100, 2) if rs else 0.0,
            "average_r": round(sum(rs) / len(rs), 3) if rs else 0.0,
            "total_r": round(sum(rs), 3),
            "average_win_r": round(sum(wins) / len(wins), 3) if wins else 0.0,
            "average_loss_r": round(sum(losses) / len(losses), 3) if losses else 0.0,
        }
