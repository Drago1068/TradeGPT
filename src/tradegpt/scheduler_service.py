from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .persistence import PersistentAuditStore
from .scan_audit import scan_completed, scan_failed, scan_missed, scan_no_plan, scan_started, ScanRun
from .scheduler import ScanSchedule, default_production_schedule, due_scans, next_run, scheduled_datetime


@dataclass(frozen=True)
class SchedulerStatus:
    timezone: str
    next_scan_id: str | None
    next_run_at: datetime | None
    scans: tuple[dict[str, object], ...]


class SchedulerService:
    """Application service for the three production scan schedule.

    It owns schedule evaluation and durable run-state recording while keeping
    actual market-data/scan execution outside the scheduler boundary.
    """

    RUN_EVENT_TYPES = {"SCAN_COMPLETED", "SCAN_FAILED", "SCAN_MISSED", "SCAN_NO_PLAN"}

    def __init__(self, audit_store: PersistentAuditStore, schedules: tuple[ScanSchedule, ...] | None = None) -> None:
        self.audit_store = audit_store
        self.schedules = schedules or default_production_schedule()

    @staticmethod
    def _normalize_now(now: datetime | None) -> datetime:
        """Return a valid timezone-aware clock value.

        FastAPI dependency/default objects must never leak into the business
        service when an endpoint helper is invoked internally.
        """
        if not isinstance(now, datetime) or now.tzinfo is None:
            return datetime.now(timezone.utc)
        return now

    def due(self, now: datetime | None = None) -> tuple[ScanSchedule, ...]:
        moment = self._normalize_now(now)
        events = self.audit_store.list()
        last_run: dict[str, datetime] = {}
        for event in events:
            scan_id = event.payload.get("scan_id")
            if not isinstance(scan_id, str) or event.event_type not in self.RUN_EVENT_TYPES:
                continue
            logical_run_at = self._scheduled_at_from_event(event.payload)
            if logical_run_at is None:
                # Backward compatibility for older audit events that predate
                # the durable scheduled_at payload field.
                logical_run_at = event.timestamp
            previous = last_run.get(scan_id)
            if previous is None or logical_run_at > previous:
                last_run[scan_id] = logical_run_at
        return due_scans(moment, self.schedules, last_run=last_run)

    @staticmethod
    def _scheduled_at_from_event(payload: dict[str, object]) -> datetime | None:
        value = payload.get("scheduled_at")
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        return parsed

    def status(self, now: datetime | None = None) -> SchedulerStatus:
        moment = self._normalize_now(now)
        upcoming = next_run(moment, self.schedules)
        events = self.audit_store.list()
        scans: list[dict[str, object]] = []
        for schedule in self.schedules:
            matching = [e for e in events if e.payload.get("scan_id") == schedule.id]
            last = matching[-1] if matching else None
            scans.append({
                "id": schedule.id,
                "label": schedule.label,
                "time_et": schedule.time_et.isoformat(timespec="minutes"),
                "enabled": schedule.enabled,
                "last_event_type": None if last is None else last.event_type,
                "last_event_at": None if last is None else last.timestamp,
            })
        return SchedulerStatus(
            timezone="America/New_York",
            next_scan_id=None if upcoming is None else upcoming[0].id,
            next_run_at=None if upcoming is None else upcoming[1],
            scans=tuple(scans),
        )

    def start(self, scan_id: str, scheduled_at: datetime, started_at: datetime | None = None) -> ScanRun:
        self._require_scan(scan_id)
        return scan_started(self.audit_store, scan_id, scheduled_at, started_at)

    def complete(self, run: ScanRun, completed_at: datetime | None = None) -> ScanRun:
        self._require_scan(run.scan_id)
        return scan_completed(self.audit_store, run, completed_at)

    def record_non_success(self, run: ScanRun, status: str, processed: int = 0, detected_at: datetime | None = None) -> ScanRun:
        self._require_scan(run.scan_id)
        if status == "NO_PLAN":
            return scan_no_plan(self.audit_store, run, processed, detected_at)
        raise ValueError(f"unsupported non-success scan status: {status}")

    def fail(self, run: ScanRun, error: str, failed_at: datetime | None = None) -> ScanRun:
        self._require_scan(run.scan_id)
        return scan_failed(self.audit_store, run, error, failed_at)

    def missed(self, scan_id: str, scheduled_at: datetime, detected_at: datetime | None = None) -> None:
        self._require_scan(scan_id)
        scan_missed(self.audit_store, scan_id, scheduled_at, detected_at)

    def scheduled_at(self, scan_id: str, now: datetime | None = None) -> datetime:
        self._require_scan(scan_id)
        moment = self._normalize_now(now)
        schedule = next(s for s in self.schedules if s.id == scan_id)
        return scheduled_datetime(moment, schedule)

    def _require_scan(self, scan_id: str) -> None:
        if scan_id not in {schedule.id for schedule in self.schedules}:
            raise KeyError(f"unknown production scan: {scan_id}")
