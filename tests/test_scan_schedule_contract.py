from tradegpt.scheduler import PRODUCTION_SCAN_IDS, default_production_schedule


def test_production_scan_schedule_contract():
    schedule = default_production_schedule()
    assert [item.id for item in schedule] == list(PRODUCTION_SCAN_IDS)
    assert [(item.time_et.hour, item.time_et.minute) for item in schedule] == [(8, 0), (10, 15), (15, 0)]
    assert all(item.time_et.tzinfo is None for item in schedule)


def test_schedule_does_not_embed_order_execution():
    schedule = default_production_schedule()
    assert all("order" not in item.id.lower() for item in schedule)
