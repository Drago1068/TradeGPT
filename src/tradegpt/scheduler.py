from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
PRODUCTION_SCAN_IDS = (
    "daily-discovery",
    "primary-qualification",
    "midday-discovery",
)


def _observed_fixed_holiday(year: int, month: int, day: int) -> date:
    holiday = date(year, month, day)
    if holiday.weekday() == 5:
        return holiday - timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + timedelta(days=1)
    return holiday


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    """Gregorian computus; used to derive NYSE Good Friday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def nyse_holidays(year: int) -> frozenset[date]:
    """Return full-day NYSE holidays for the supplied Gregorian year.

    This intentionally models full-day closures only. The production scans all
    occur well before the normal NYSE early-close window, so early-close rules
    do not affect the three-scan contract.
    """
    new_year = _observed_fixed_holiday(year, 1, 1)
    good_friday = _easter_sunday(year) - timedelta(days=2)
    return frozenset(
        {
            new_year,
            _nth_weekday(year, 1, 0, 3),   # Martin Luther King Jr. Day
            _nth_weekday(year, 2, 0, 3),   # Presidents Day
            good_friday,
            _last_weekday(year, 5, 0),     # Memorial Day
            _observed_fixed_holiday(year, 6, 19),  # Juneteenth
            _observed_fixed_holiday(year, 7, 4),   # Independence Day
            _nth_weekday(year, 9, 0, 1),   # Labor Day
            _nth_weekday(year, 11, 3, 4),  # Thanksgiving
            _observed_fixed_holiday(year, 12, 25), # Christmas
        }
    )


def is_market_holiday(day: date) -> bool:
    return day in nyse_holidays(day.year)


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
    local_day = moment.astimezone(EASTERN).date()
    return local_day.weekday() < 5 and not is_market_holiday(local_day)


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
    if not is_scan_day(local_now):
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
        if is_scan_day(cursor):
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
