from datetime import datetime
from zoneinfo import ZoneInfo

from tradegpt.scheduler_service import SchedulerService
from tradegpt.scan_audit import ScanRun


EASTERN = ZoneInfo("America/New_York")


def et(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=EASTERN)


class FakeAuditStore:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)
        return event

    def list(self, event_type=None):
        if event_type is None:
            return list(self.events)
        return [e for e in self.events if e.event_type == event_type]


def test_service_exposes_next_run_and_three_scans():
    service = SchedulerService(FakeAuditStore())
    status = service.status(et(2026, 9, 7, 7, 0))
    assert status.next_scan_id == "daily-discovery"
    assert status.next_run_at == et(2026, 9, 7, 8, 0)
    assert len(status.scans) == 3


def test_service_run_lifecycle_is_durable_and_removes_scan_from_due():
    store = FakeAuditStore()
    service = SchedulerService(store)
    now = et(2026, 9, 7, 8, 5)
    assert [s.id for s in service.due(now)] == ["daily-discovery"]
    run = service.start("daily-discovery", et(2026, 9, 7, 8, 0), now)
    service.complete(run, et(2026, 9, 7, 8, 2))
    assert [s.id for s in service.due(now)] == ["primary-qualification"]


def test_service_failure_counts_as_run_for_duplicate_prevention():
    store = FakeAuditStore()
    service = SchedulerService(store)
    now = et(2026, 9, 7, 10, 20)
    run = service.start("primary-qualification", et(2026, 9, 7, 10, 15), now)
    service.fail(run, "provider unavailable", et(2026, 9, 7, 10, 16))
    assert "primary-qualification" not in [s.id for s in service.due(now)]


def test_service_missed_scan_counts_as_run():
    store = FakeAuditStore()
    service = SchedulerService(store)
    now = et(2026, 9, 7, 12, 40)
    service.missed("midday-discovery", et(2026, 9, 7, 12, 30), now)
    assert "midday-discovery" not in [s.id for s in service.due(now)]


def test_service_rejects_unknown_scan():
    service = SchedulerService(FakeAuditStore())
    try:
        service.start("not-a-production-scan", et(2026, 9, 7, 8, 0))
    except KeyError as exc:
        assert "unknown production scan" in str(exc)
    else:
        raise AssertionError("unknown scan was accepted")


def test_service_can_compute_scheduled_time():
    service = SchedulerService(FakeAuditStore())
    assert service.scheduled_at("midday-discovery", et(2026, 9, 7, 7, 0)) == et(2026, 9, 7, 12, 30)


def test_service_accepts_scan_run_for_completion():
    store = FakeAuditStore()
    service = SchedulerService(store)
    run = ScanRun("daily-discovery", et(2026, 9, 7, 8, 0), et(2026, 9, 7, 8, 0))
    result = service.complete(run, et(2026, 9, 7, 8, 1))
    assert result.status == "COMPLETED"
