from datetime import datetime, timezone

from tradegpt.db import init_db, make_engine, make_session_factory
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
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    return SchedulerService(PersistentAuditStore(make_session_factory(engine)))


def test_worker_executes_due_scan_once_and_audits_completion():
    scheduler = _service()
    executor = FakeExecutor()
    worker = SchedulerWorker(scheduler, executor)
    now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    first = worker.run_due(now)
    second = worker.run_due(now)
    assert [r.status for r in first] == ["COMPLETED"]
    assert second == ()
    assert len(executor.calls) == 1
    assert executor.calls[0][0] == "daily-discovery"
    assert [e.event_type for e in scheduler.audit_store.list()] == ["SCAN_STARTED", "SCAN_COMPLETED"]


def test_worker_failure_is_audited_and_not_retried_for_same_window():
    scheduler = _service()
    executor = FakeExecutor(RuntimeError("provider unavailable"))
    worker = SchedulerWorker(scheduler, executor)
    now = datetime(2026, 9, 7, 14, 15, tzinfo=timezone.utc)
    result = worker.run_due(now)
    again = worker.run_due(now)
    assert result[0].status == "FAILED"
    assert "provider unavailable" in (result[0].error or "")
    assert again == ()
    assert len(executor.calls) == 1
    assert [e.event_type for e in scheduler.audit_store.list()] == ["SCAN_STARTED", "SCAN_FAILED"]


def test_worker_requires_due_schedule():
    scheduler = _service()
    executor = FakeExecutor()
    worker = SchedulerWorker(scheduler, executor)
    now = datetime(2026, 9, 7, 11, 59, tzinfo=timezone.utc)
    assert worker.run_due(now) == ()
    assert executor.calls == []
    assert scheduler.audit_store.list() == []


def test_worker_executes_all_due_windows_after_restart():
    scheduler = _service()
    executor = FakeExecutor()
    worker = SchedulerWorker(scheduler, executor)
    now = datetime(2026, 9, 7, 17, 0, tzinfo=timezone.utc)
    results = worker.run_due(now)
    assert [r.scan_id for r in results] == ["daily-discovery", "primary-qualification", "midday-discovery"]
    assert len(executor.calls) == 3
    assert len(scheduler.audit_store.list()) == 6


def test_worker_records_executor_failure_without_raising():
    scheduler = _service()
    executor = FakeExecutor(ValueError("bad provider payload"))
    worker = SchedulerWorker(scheduler, executor)
    schedule = next(s for s in scheduler.schedules if s.id == "daily-discovery")
    scheduled = scheduler.scheduled_at(schedule.id, datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc))
    result = worker.run_one(schedule, scheduled)
    assert result.status == "FAILED"
    assert result.error == "ValueError: bad provider payload"
    assert scheduler.audit_store.list()[-1].event_type == "SCAN_FAILED"
