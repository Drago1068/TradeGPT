from datetime import datetime, timezone

from sqlalchemy import inspect

from tradegpt.composition import EmptyScanPlanProvider, build_runtime, build_scheduler_worker
from tradegpt.db import make_engine


def test_default_composition_is_safe_and_initializes_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'tradegpt.db'}"
    scheduler, worker = build_scheduler_worker(database_url=database_url, equity=2905)

    due = worker.run_due(datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc))

    assert len(due) == 1
    assert due[0].scan_id == "daily-discovery"
    assert due[0].status == "NO_PLAN"
    assert len(scheduler.status(datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)).scans) == 3
    tables = set(inspect(make_engine(database_url)).get_table_names())
    assert {"candidates", "audit_events", "learning_records"}.issubset(tables)


def test_runtime_exposes_one_shared_persistence_graph(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    runtime = build_runtime(database_url=database_url, equity=2905)

    assert runtime.scheduler is not None
    assert runtime.worker is not None
    assert runtime.candidate_store is not None
    assert runtime.audit_store is not None
    assert runtime.learning_store is not None
    assert runtime.engine is not None
    assert runtime.market_data_configured is False
    assert runtime.scan_plan_configured is False
    assert runtime.worker.scheduler is runtime.scheduler
    assert runtime.worker.executor.candidate_store is runtime.candidate_store
    assert runtime.worker.executor.audit_store is runtime.audit_store
    assert runtime.worker.executor.learning_store is runtime.learning_store


def test_configured_runtime_reports_data_and_plan_readiness(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'configured.db'}"

    class Provider:
        is_configured = True

        def as_provider(self):
            return self

        def snapshot(self, symbol):
            raise AssertionError("not called by composition readiness test")

    class PlanProvider:
        def requests(self, scan_id, scheduled_at):
            return ()

    runtime = build_runtime(
        database_url=database_url,
        provider=Provider(),
        plan_provider=PlanProvider(),
        equity=2905,
    )

    assert runtime.market_data_configured is True
    assert runtime.scan_plan_configured is True


def test_empty_plan_provider_has_no_symbols():
    provider = EmptyScanPlanProvider()
    assert provider.requests("daily-discovery", datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)) == ()
