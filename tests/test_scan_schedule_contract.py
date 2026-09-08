from datetime import datetime

from tradegpt.scheduler_service import SchedulerService


def test_production_scan_schedule_contract():
    schedule = SchedulerService.production_schedule()
    assert [item.scan_id for item in schedule] == [
        "daily-sniper-discovery",
        "v2-confirmation",
        "midday-monitor",
    ]
    assert [(item.hour, item.minute) for item in schedule] == [(8, 0), (10, 15), (12, 30)]
    assert all(item.timezone == "America/New_York" for item in schedule)


def test_schedule_does_not_embed_order_execution():
    schedule = SchedulerService.production_schedule()
    assert all("order" not in item.scan_id.lower() for item in schedule)
