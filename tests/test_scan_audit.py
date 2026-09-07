from datetime import datetime, timezone

from tradegpt.persistence import PersistentAuditStore
from tradegpt.scan_audit import scan_completed, scan_failed, scan_missed, scan_started


def test_scan_lifecycle_persists_audit_events() -> None:
    store = PersistentAuditStore()
    scheduled = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    started = scan_started(store, "daily-discovery", scheduled, scheduled)
    completed = scan_completed(store, started, datetime(2026, 9, 7, 12, 1, tzinfo=timezone.utc))

    events = store.list()
    assert [event.event_type for event in events[-2:]] == ["SCAN_STARTED", "SCAN_COMPLETED"]
    assert completed.status == "COMPLETED"


def test_scan_failure_records_error() -> None:
    store = PersistentAuditStore()
    scheduled = datetime(2026, 9, 7, 14, 15, tzinfo=timezone.utc)
    run = scan_started(store, "primary-qualification", scheduled, scheduled)
    failed = scan_failed(store, run, "provider timeout", scheduled)

    assert failed.status == "FAILED"
    assert failed.error == "provider timeout"
    assert store.list()[-1].event_type == "SCAN_FAILED"
    assert store.list()[-1].payload["error"] == "provider timeout"


def test_missed_scan_records_schedule_identity() -> None:
    store = PersistentAuditStore()
    scheduled = datetime(2026, 9, 7, 16, 30, tzinfo=timezone.utc)
    scan_missed(store, "midday-discovery", scheduled, datetime(2026, 9, 7, 16, 35, tzinfo=timezone.utc))

    event = store.list()[-1]
    assert event.event_type == "SCAN_MISSED"
    assert event.payload["scan_id"] == "midday-discovery"
