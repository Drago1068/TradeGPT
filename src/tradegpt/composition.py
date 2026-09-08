from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Sequence

from .db import make_engine, make_session_factory
from .discovery import EmptyProductionDiscoveryPlan, ProductionDiscoveryPlan
from .migrations import migrate
from .persistence import PersistentAuditStore, PersistentCandidateStore, PersistentLearningStore
from .providers.factory import build_market_data_provider
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


class EmptyScanPlanProvider(EmptyProductionDiscoveryPlan):
    """Backward-compatible alias for the safe empty production discovery plan."""


@dataclass(frozen=True)
class TradeGPTRuntime:
    """Canonical application dependency graph shared by API and worker paths."""

    scheduler: SchedulerService
    worker: SchedulerWorker
    candidate_store: PersistentCandidateStore
    audit_store: PersistentAuditStore
    learning_store: PersistentLearningStore
    engine: object
    market_data_configured: bool
    scan_plan_configured: bool


def build_runtime(
    *,
    plan_provider: ScanPlanProvider | Callable[[str, datetime], Sequence[QualificationRequest]] | None = None,
    database_url: str | None = None,
    provider=None,
    equity: float | None = None,
) -> TradeGPTRuntime:
    """Build the complete production runtime with one shared persistence graph."""
    engine = make_engine(database_url)
    migrate(engine)
    session_factory = make_session_factory(engine)
    audit_store = PersistentAuditStore(session_factory)
    candidate_store = PersistentCandidateStore(session_factory)
    learning_store = PersistentLearningStore(session_factory)

    configured_provider = provider or build_market_data_provider()
    market_provider = configured_provider.as_provider()
    configured_plan_provider = plan_provider or EmptyProductionDiscoveryPlan()
    qualification = QualificationService(market_provider)
    executor = ScanExecutorService(
        plan_provider=configured_plan_provider,
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
        engine=engine,
        market_data_configured=bool(getattr(configured_provider, "is_configured", False)),
        scan_plan_configured=not isinstance(configured_plan_provider, EmptyProductionDiscoveryPlan),
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
