from datetime import datetime, timezone

import pytest

from tradegpt.forward_learning import evaluate_learning_record
from tradegpt.learning import LearningRecord
from tradegpt.models import CandidateState


class FakeStore:
    def __init__(self, record: LearningRecord | None):
        self.record = record
        self.updated = False

    def get(self, record_id: int):
        return self.record if record_id == 1 else None

    def update(self, record_id: int, record: LearningRecord) -> None:
        assert record_id == 1
        self.record = record
        self.updated = True


def make_record() -> LearningRecord:
    return LearningRecord(
        symbol="TEST",
        discovered_at=datetime.now(timezone.utc),
        discovery_score=92.0,
        discovery_state=CandidateState.TRADE_READY,
        trigger_confirmed=True,
        trade_ready=True,
    )


def test_target_is_persisted_as_resolved_outcome():
    store = FakeStore(make_record())
    result = evaluate_learning_record(
        store,
        record_id=1,
        entry_price=10,
        stop_price=9,
        target_price=12,
        prices=[10.2, 10.8, 11.4, 12.0],
        evaluated_at=datetime(2026, 9, 7, tzinfo=timezone.utc),
    )

    assert result is not None
    assert result.result == "TARGET"
    assert result.outcome_r == 2.0
    assert store.updated is True
    assert store.record.outcome is not None
    assert store.record.outcome.exit_price == 12
    assert store.record.outcome.result == "TARGET"


def test_stop_is_persisted_as_resolved_outcome():
    store = FakeStore(make_record())
    result = evaluate_learning_record(
        store,
        record_id=1,
        entry_price=10,
        stop_price=9,
        target_price=12,
        prices=[9.8, 9.4, 9.0],
    )

    assert result is not None
    assert result.result == "STOPPED"
    assert result.outcome_r == -1.0
    assert store.record.outcome.exit_price == 9


def test_open_path_remains_unresolved_and_is_not_persisted():
    store = FakeStore(make_record())
    result = evaluate_learning_record(
        store,
        record_id=1,
        entry_price=10,
        stop_price=9,
        target_price=12,
        prices=[10.1, 10.4, 10.7],
    )

    assert result is None
    assert store.updated is False
    assert store.record.outcome is None


def test_missing_record_is_rejected():
    store = FakeStore(None)
    with pytest.raises(KeyError):
        evaluate_learning_record(
            store,
            record_id=1,
            entry_price=10,
            stop_price=9,
            target_price=12,
            prices=[12],
        )


def test_resolved_record_cannot_be_evaluated_twice():
    store = FakeStore(make_record())
    evaluate_learning_record(
        store,
        record_id=1,
        entry_price=10,
        stop_price=9,
        target_price=12,
        prices=[12],
    )

    with pytest.raises(ValueError, match="already has an outcome"):
        evaluate_learning_record(
            store,
            record_id=1,
            entry_price=10,
            stop_price=9,
            target_price=12,
            prices=[9],
        )


def test_invalid_geometry_is_rejected_without_update():
    store = FakeStore(make_record())
    with pytest.raises(ValueError, match="stop_price"):
        evaluate_learning_record(
            store,
            record_id=1,
            entry_price=10,
            stop_price=10,
            target_price=12,
            prices=[12],
        )
    assert store.updated is False
