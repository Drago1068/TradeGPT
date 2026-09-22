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


def test_scan_started_records_lateness_and_timeliness():
    store = PersistentAuditStore()
    scheduled = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    started = datetime(2026, 9, 7, 12, 31, tzinfo=timezone.utc)
    scan_started(store, "daily-discovery", scheduled, started)
    payload = store.list()[-1].payload
    assert payload["lateness_seconds"] == 1860.0
    assert payload["timeliness"] == "MISSED_RECOVERY"


def test_scan_completed_preserves_actual_execution_timestamp():
    store = PersistentAuditStore()
    scheduled = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    started = datetime(2026, 9, 7, 12, 1, tzinfo=timezone.utc)
    completed_at = datetime(2026, 9, 7, 12, 2, tzinfo=timezone.utc)
    run = scan_started(store, "daily-discovery", scheduled, started)
    scan_completed(store, run, completed_at)
    payload = store.list()[-1].payload
    assert payload["started_at"] == started.isoformat()
    assert payload["actual_execution_at"] == completed_at.isoformat()
