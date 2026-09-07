from datetime import datetime, timezone

from sqlalchemy import inspect

from tradegpt.composition import EmptyScanPlanProvider, build_scheduler_worker
from tradegpt.db import make_engine


def test_default_composition_is_safe_and_initializes_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'tradegpt.db'}"
    scheduler, worker = build_scheduler_worker(database_url=database_url, equity=2905)

    due = worker.run_due(datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc))

    assert due == ()
    assert len(scheduler.status(datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)).scans) == 3
    tables = set(inspect(make_engine(database_url)).get_table_names())
    assert {"candidates", "audit_events", "learning_records"}.issubset(tables)


def test_empty_plan_provider_has_no_symbols():
    provider = EmptyScanPlanProvider()
    assert provider.requests("daily_sniper", datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)) == ()
