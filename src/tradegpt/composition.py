from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Sequence

from .db import init_db, make_engine, make_session_factory
from .persistence import PersistentAuditStore, PersistentCandidateStore, PersistentLearningStore
from .providers.configured import ConfiguredMarketDataProvider
from .qualification import QualificationRequest, QualificationService
from .scan_executor import ScanExecutorService, ScanPlanProvider
from .scheduler_service import SchedulerService
from .worker import SchedulerWorker


def _equity_from_environment() -> float:
    raw = os.getenv("TRADEGPT_EQUITY", "2905")
    try:
        equity = float(raw)
    except ValueError as exc:
        raise RuntimeError("TRADEGPT_EQUITY must be numeric") from exc
    if equity <= 0:
        raise RuntimeError("TRADEGPT_EQUITY must be positive")
    return equity


class EmptyScanPlanProvider:
    """Safe production default until a real discovery engine is configured."""

    def requests(self, scan_id: str, scheduled_at: datetime) -> Sequence[QualificationRequest]:
        return ()


@dataclass(frozen=True)
class TradeGPTRuntime:
    """Canonical application dependency graph shared by API and worker paths."""

    scheduler: SchedulerService
    worker: SchedulerWorker
    candidate_store: PersistentCandidateStore
    audit_store: PersistentAuditStore
    learning_store: PersistentLearningStore


def build_runtime(
    *,
    plan_provider: ScanPlanProvider | Callable[[str, datetime], Sequence[QualificationRequest]] | None = None,
    database_url: str | None = None,
    provider=None,
    equity: float | None = None,
) -> TradeGPTRuntime:
    """Build the complete production runtime with one shared persistence graph.

    The default graph is deliberately safe: no discovery plan and no broker
    connectivity. Supplying a plan provider adds discovery without changing the
    worker or qualification boundaries.
    """
    engine = make_engine(database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    audit_store = PersistentAuditStore(session_factory)
    candidate_store = PersistentCandidateStore(session_factory)
    learning_store = PersistentLearningStore(session_factory)

    market_provider = provider or ConfiguredMarketDataProvider().as_provider()
    qualification = QualificationService(market_provider)
    executor = ScanExecutorService(
        plan_provider=plan_provider or EmptyScanPlanProvider(),
        qualification=qualification,
        candidate_store=candidate_store,
        learning_store=learning_store,
        audit_store=audit_store,
        equity=equity if equity is not None else _equity_from_environment(),
    )
    scheduler = SchedulerService(audit_store)
    worker = SchedulerWorker(scheduler, executor)
    return TradeGPTRuntime(
        scheduler=scheduler,
        worker=worker,
        candidate_store=candidate_store,
        audit_store=audit_store,
        learning_store=learning_store,
    )


def build_scheduler_worker(
    *,
    plan_provider: ScanPlanProvider | Callable[[str, datetime], Sequence[QualificationRequest]] | None = None,
    database_url: str | None = None,
    provider=None,
    equity: float | None = None,
) -> tuple[SchedulerService, SchedulerWorker]:
    """Backward-compatible builder returning only scheduler and worker."""
    runtime = build_runtime(
        plan_provider=plan_provider,
        database_url=database_url,
        provider=provider,
        equity=equity,
    )
    return runtime.scheduler, runtime.worker
