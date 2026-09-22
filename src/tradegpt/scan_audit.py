from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .ledger import AuditEvent
from .persistence import PersistentAuditStore
from .scheduler import SCHEDULE_GRACE_MINUTES, SCHEDULE_MISSED_MINUTES


@dataclass(frozen=True)
class ScanRun:
    scan_id: str
    scheduled_at: datetime
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "STARTED"
    error: str | None = None


def scan_started(store: PersistentAuditStore, scan_id: str, scheduled_at: datetime, started_at: datetime | None = None) -> ScanRun:
    started = started_at or datetime.now(timezone.utc)
    run = ScanRun(scan_id=scan_id, scheduled_at=scheduled_at, started_at=started)
    lateness_seconds = max(0.0, (started - scheduled_at).total_seconds())
    if lateness_seconds > SCHEDULE_MISSED_MINUTES * 60:
        timeliness = "MISSED_RECOVERY"
    elif lateness_seconds > SCHEDULE_GRACE_MINUTES * 60:
        timeliness = "LATE"
    else:
        timeliness = "ON_TIME"
    store.append(AuditEvent(event_type="SCAN_STARTED", symbol=None, payload={
        "scan_id": scan_id,
        "scheduled_at": scheduled_at.isoformat(),
        "started_at": started.isoformat(),
        "lateness_seconds": lateness_seconds,
        "timeliness": timeliness,
    }))
    return run


def scan_completed(store: PersistentAuditStore, run: ScanRun, completed_at: datetime | None = None) -> ScanRun:
    completed = completed_at or datetime.now(timezone.utc)
    result = ScanRun(run.scan_id, run.scheduled_at, run.started_at, completed, "COMPLETED")
    store.append(AuditEvent(event_type="SCAN_COMPLETED", symbol=None, payload={"scan_id": run.scan_id, "scheduled_at": run.scheduled_at.isoformat(), "started_at": run.started_at.isoformat(), "completed_at": completed.isoformat(), "actual_execution_at": completed.isoformat()}))
    return result


def scan_no_plan(store: PersistentAuditStore, run: ScanRun, processed: int = 0, detected_at: datetime | None = None) -> ScanRun:
    detected = detected_at or datetime.now(timezone.utc)
    result = ScanRun(run.scan_id, run.scheduled_at, run.started_at, detected, "NO_PLAN")
    store.append(AuditEvent(event_type="SCAN_NO_PLAN", symbol=None, payload={"scan_id": run.scan_id, "scheduled_at": run.scheduled_at.isoformat(), "detected_at": detected.isoformat(), "processed": processed, "reason": "scan plan provider returned no requests"}))
    return result


def scan_failed(store: PersistentAuditStore, run: ScanRun, error: str, failed_at: datetime | None = None) -> ScanRun:
    failed = failed_at or datetime.now(timezone.utc)
    result = ScanRun(run.scan_id, run.scheduled_at, run.started_at, failed, "FAILED", error)
    store.append(AuditEvent(event_type="SCAN_FAILED", symbol=None, payload={"scan_id": run.scan_id, "scheduled_at": run.scheduled_at.isoformat(), "failed_at": failed.isoformat(), "error": error}))
    return result


def scan_missed(store: PersistentAuditStore, scan_id: str, scheduled_at: datetime, detected_at: datetime | None = None) -> None:
    detected = detected_at or datetime.now(timezone.utc)
    store.append(AuditEvent(event_type="SCAN_MISSED", symbol=None, payload={"scan_id": scan_id, "scheduled_at": scheduled_at.isoformat(), "detected_at": detected.isoformat()}))
