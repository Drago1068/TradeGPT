from datetime import datetime, time

import pytest

from tradegpt.scheduler import (
    EASTERN,
    PRODUCTION_SCAN_IDS,
    ScanSchedule,
    default_production_schedule,
    due_scans,
    is_market_holiday,
    is_scan_day,
    next_run,
    validate_production_schedule,
)


def et(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=EASTERN)


def test_default_schedule_matches_three_scan_contract() -> None:
    schedules = default_production_schedule()
    assert tuple(schedule.id for schedule in schedules) == PRODUCTION_SCAN_IDS
    assert tuple(schedule.time_et for schedule in schedules) == (
        time(8, 0),
        time(10, 15),
        time(12, 30),
    )


def test_due_scans_at_exact_time_and_after() -> None:
    schedules = default_production_schedule()
    assert [s.id for s in due_scans(et(2026, 9, 8, 8, 0), schedules)] == ["daily-discovery"]
    assert [s.id for s in due_scans(et(2026, 9, 8, 10, 16), schedules)] == [
        "daily-discovery",
        "primary-qualification",
    ]


def test_last_run_prevents_duplicate_execution() -> None:
    schedules = default_production_schedule()
    now = et(2026, 9, 8, 10, 16)
    last_run = {"daily-discovery": et(2026, 9, 8, 8, 0)}
    assert [s.id for s in due_scans(now, schedules, last_run=last_run)] == [
        "primary-qualification"
    ]


def test_weekend_has_no_due_scans() -> None:
    schedules = default_production_schedule()
    saturday = et(2026, 9, 12, 12, 30)
    assert not is_scan_day(saturday)
    assert due_scans(saturday, schedules) == ()


def test_nyse_holiday_has_no_due_scans() -> None:
    schedules = default_production_schedule()
    labor_day = et(2026, 9, 7, 12, 30)
    assert is_market_holiday(labor_day.date())
    assert not is_scan_day(labor_day)
    assert due_scans(labor_day, schedules) == ()


def test_nyse_holiday_next_run_skips_labor_day() -> None:
    schedules = default_production_schedule()
    schedule, run_at = next_run(et(2026, 9, 4, 13, 0), schedules)
    assert schedule.id == "daily-discovery"
    assert run_at == et(2026, 9, 8, 8, 0)


def test_nyse_good_friday_is_closed() -> None:
    schedules = default_production_schedule()
    good_friday = et(2026, 4, 3, 12, 30)
    assert is_market_holiday(good_friday.date())
    assert due_scans(good_friday, schedules) == ()


def test_next_run_crosses_dst_start_without_fixed_offset() -> None:
    schedules = default_production_schedule()
    schedule, run_at = next_run(et(2026, 3, 6, 13, 0), schedules)
    assert schedule.id == "daily-discovery"
    assert run_at == et(2026, 3, 9, 8, 0)
    assert run_at.utcoffset().total_seconds() == -4 * 3600


def test_next_run_crosses_dst_end_without_fixed_offset() -> None:
    schedules = default_production_schedule()
    schedule, run_at = next_run(et(2026, 10, 30, 13, 0), schedules)
    assert schedule.id == "daily-discovery"
    assert run_at == et(2026, 11, 2, 8, 0)
    assert run_at.utcoffset().total_seconds() == -5 * 3600


def test_invalid_duplicate_ids_are_rejected() -> None:
    schedules = list(default_production_schedule())
    schedules[1] = ScanSchedule("daily-discovery", "Duplicate", time(9, 0))
    with pytest.raises(ValueError, match="duplicate"):
        validate_production_schedule(schedules)


def test_invalid_scan_set_is_rejected() -> None:
    schedules = [
        ScanSchedule.from_time_string("daily-discovery", "Daily", "08:00"),
        ScanSchedule.from_time_string("primary-qualification", "Primary", "10:15"),
        ScanSchedule.from_time_string("extra", "Extra", "12:30"),
    ]
    with pytest.raises(ValueError, match="ids"):
        validate_production_schedule(schedules)


def test_duplicate_enabled_times_are_rejected() -> None:
    schedules = list(default_production_schedule())
    schedules[1] = ScanSchedule("primary-qualification", "Primary", time(8, 0))
    with pytest.raises(ValueError, match="time"):
        validate_production_schedule(schedules)


def test_invalid_time_string_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid ET scan time"):
        ScanSchedule.from_time_string("daily-discovery", "Daily", "8am")


def test_next_run_returns_none_when_all_scans_disabled() -> None:
    schedules = [
        ScanSchedule(s.id, s.label, s.time_et, enabled=False)
        for s in default_production_schedule()
    ]
    assert next_run(et(2026, 9, 8, 7, 0), schedules) is None
