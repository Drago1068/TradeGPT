from datetime import datetime, timezone

import pytest

from tradegpt.persistence import PersistentAuditStore
from tradegpt.scheduler_service import SchedulerService
from tradegpt.worker import SchedulerWorker


class FakeExecutor:
    def __init__(self, error: Exception | None = None):
        self.calls = []
        self.error = error

    def execute(self, scan_id: str, scheduled_at: datetime) -> None:
        self.calls.append((scan_id, scheduled_at))
        if self.error:
            raise self.error


def _service() -> SchedulerService:
    return SchedulerService(PersistentAuditStore())


def test_worker_executes_due_scan_once_and_audits_completion():
    scheduler = _service()
    executor = FakeExecutor()
    worker = SchedulerWorker(scheduler, executor)
    now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)  # 08:00 ET

    first = worker.run_due(now)
    second = worker.run_due(now)

    assert [r.status for r in first] == ["COMPLETED"]
    assert second == ()
    assert len(executor.calls) == 1
    assert executor.calls[0][0] == "daily-discovery"
    events = scheduler.audit_store.list()
    assert [e.event_type for e in events] == ["SCAN_STARTED", "SCAN_COMPLETED"]


def test_worker_failure_is_audited_and_is_not_retried_for_same_window():
    scheduler = _service()
    executor = FakeExecutor(RuntimeError("provider unavailable"))
    worker = SchedulerWorker(scheduler, executor)
    now = datetime(2026, 9, 7, 14, 15, tzinfo=timezone.utc)  # 10:15 ET

    result = worker.run_due(now)
    again = worker.run_due(now)

    assert [r.status for r in result] == ["FAILED"]
    assert "provider unavailable" in (result[0].error or "")
    assert again == ()
    assert len(executor.calls) == 1
    events = scheduler.audit_store.list()
    assert [e.event_type for e in events] == ["SCAN_STARTED", "SCAN_FAILED"]


def test_worker_requires_due_schedule_for_normal_operation():
    scheduler = _service()
    executor = FakeExecutor()
    worker = SchedulerWorker(scheduler, executor)
    now = datetime(2026, 9, 7, 11, 59, tzinfo=timezone.utc)  # 07:59 ET

    assert worker.run_due(now) == ()
    assert executor.calls == []
    assert scheduler.audit_store.list() == []


def test_worker_can_execute_multiple_due_windows_after_restart():
    scheduler = _service()
    executor = FakeExecutor()
    worker = SchedulerWorker(scheduler, executor)
    now = datetime(2026, 9, 7, 17, 0, tzinfo=timezone.utc)  # 13:00 ET

    results = worker.run_due(now)

    assert [r.scan_id for r in results] == [
        "daily-discovery",
        "primary-qualification",
        "midday-discovery",
    ]
    assert len(executor.calls) == 3
    assert len(scheduler.audit_store.list()) == 6


def test_worker_propagates_only_audited_failure_not_exception():
    scheduler = _service()
    executor = FakeExecutor(ValueError("bad provider payload"))
    worker = SchedulerWorker(scheduler, executor)
    schedule = next(s for s in scheduler.schedules if s.id == "daily-discovery")
    scheduled = scheduler.scheduled_at(schedule.id, datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc))

    result = worker.run_one(schedule, scheduled)

    assert result.status == "FAILED"
    assert result.error == "ValueError: bad provider payload"
    assert scheduler.audit_store.list()[-1].event_type == "SCAN_FAILED"
