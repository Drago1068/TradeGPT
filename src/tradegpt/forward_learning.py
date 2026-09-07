from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, Sequence

from .forward_test import ForwardTestResult, evaluate_path
from .learning import LearningRecord, Outcome


class LearningStore(Protocol):
    def get(self, record_id: int) -> LearningRecord | None: ...
    def update(self, record_id: int, record: LearningRecord) -> None: ...


def evaluate_learning_record(
    store: LearningStore,
    *,
    record_id: int,
    entry_price: float,
    stop_price: float,
    target_price: float,
    prices: Sequence[float],
    evaluated_at: datetime | None = None,
) -> ForwardTestResult | None:
    """Forward-test one persistent learning record and persist only resolved outcomes.

    OPEN paths remain unresolved so the learning summary cannot treat a still-active
    path as a completed trade. A record that already has an outcome is immutable from
    this service to prevent duplicate/conflicting evaluations.
    """
    record = store.get(record_id)
    if record is None:
        raise KeyError(f"learning record {record_id} not found")
    if record.outcome is not None:
        raise ValueError(f"learning record {record_id} already has an outcome")

    result = evaluate_path(
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        prices=prices,
    )
    if result.result == "OPEN":
        return None

    timestamp = evaluated_at or datetime.now(timezone.utc)
    record.outcome = Outcome(
        symbol=record.symbol,
        evaluated_at=timestamp,
        entry_price=entry_price,
        exit_price=target_price if result.result == "TARGET" else stop_price,
        stop_price=stop_price,
        target_price=target_price,
        outcome_r=result.outcome_r,
        max_adverse_excursion_r=result.max_adverse_excursion_r,
        max_favorable_excursion_r=result.max_favorable_excursion_r,
        result=result.result,
    )
    store.update(record_id, record)
    return result
