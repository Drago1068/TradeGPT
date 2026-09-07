from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
PRODUCTION_SCAN_IDS = (
    "daily-discovery",
    "primary-qualification",
    "midday-discovery",
)


@dataclass(frozen=True)
class ScanSchedule:
    id: str
    label: str
    time_et: time
    enabled: bool = True

    @classmethod
    def from_time_string(
        cls, scan_id: str, label: str, time_et: str, enabled: bool = True
    ) -> "ScanSchedule":
        try:
            parsed = time.fromisoformat(time_et)
        except ValueError as exc:
            raise ValueError(f"invalid ET scan time for {scan_id}: {time_et!r}") from exc
        if parsed.second or parsed.microsecond:
            raise ValueError(f"scan time must be HH:MM for {scan_id}")
        return cls(scan_id, label, parsed, enabled)


def validate_production_schedule(schedules: list[ScanSchedule]) -> tuple[ScanSchedule, ...]:
    if len(schedules) != len(PRODUCTION_SCAN_IDS):
        raise ValueError("production schedule must contain exactly three scans")
    ids = tuple(schedule.id for schedule in schedules)
    if len(set(ids)) != len(ids):
        raise ValueError("production schedule contains duplicate scan ids")
    if set(ids) != set(PRODUCTION_SCAN_IDS):
        raise ValueError("production schedule ids do not match the production contract")
    enabled_times: set[time] = set()
    for schedule in schedules:
        if schedule.enabled:
            if schedule.time_et in enabled_times:
                raise ValueError("enabled production scans cannot share a scheduled time")
            enabled_times.add(schedule.time_et)
    return tuple(sorted(schedules, key=lambda schedule: schedule.time_et))


def is_scan_day(moment: datetime) -> bool:
    return moment.astimezone(EASTERN).weekday() < 5


def scheduled_datetime(moment: datetime, schedule: ScanSchedule) -> datetime:
    local = moment.astimezone(EASTERN)
    return datetime.combine(local.date(), schedule.time_et, tzinfo=EASTERN)


def due_scans(
    now: datetime,
    schedules: list[ScanSchedule] | tuple[ScanSchedule, ...],
    *,
    last_run: dict[str, datetime] | None = None,
) -> tuple[ScanSchedule, ...]:
    """Return enabled scans whose ET scheduled time has arrived today.

    A scan is due once per ET calendar day. ``last_run`` prevents duplicate
    execution after a worker restart or repeated scheduler ticks.
    """
    validate_production_schedule(list(schedules))
    local_now = now.astimezone(EASTERN)
    if local_now.weekday() >= 5:
        return ()
    last_run = last_run or {}
    due: list[ScanSchedule] = []
    for schedule in schedules:
        if not schedule.enabled:
            continue
        scheduled = scheduled_datetime(local_now, schedule)
        if local_now >= scheduled:
            previous = last_run.get(schedule.id)
            if previous is None or previous.astimezone(EASTERN).date() != local_now.date():
                due.append(schedule)
    return tuple(sorted(due, key=lambda item: item.time_et))


def next_run(
    now: datetime,
    schedules: list[ScanSchedule] | tuple[ScanSchedule, ...],
) -> tuple[ScanSchedule, datetime] | None:
    """Return the next enabled production scan in America/New_York time."""
    ordered = validate_production_schedule(list(schedules))
    local_now = now.astimezone(EASTERN)
    cursor = local_now
    for _ in range(8):
        if cursor.weekday() < 5:
            for schedule in ordered:
                if not schedule.enabled:
                    continue
                candidate = scheduled_datetime(cursor, schedule)
                if candidate > local_now:
                    return schedule, candidate
        cursor = datetime.combine(
            cursor.date() + timedelta(days=1), time.min, tzinfo=EASTERN
        )
    return None


def default_production_schedule() -> tuple[ScanSchedule, ...]:
    return validate_production_schedule(
        [
            ScanSchedule.from_time_string("daily-discovery", "Daily Sniper Discovery", "08:00"),
            ScanSchedule.from_time_string("primary-qualification", "V2 Qualification", "10:15"),
            ScanSchedule.from_time_string("midday-discovery", "Midday Second-Wave Discovery", "12:30"),
        ]
    )
