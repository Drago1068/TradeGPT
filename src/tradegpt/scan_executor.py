from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol, Sequence

from .learning import LearningRecord
from .persistence import PersistentAuditStore, PersistentCandidateStore, PersistentLearningStore
from .qualification import QualificationRequest, QualificationService


class ScanPlanProvider(Protocol):
    def requests(self, scan_id: str, scheduled_at: datetime) -> Sequence[QualificationRequest]: ...


@dataclass(frozen=True)
class ScanExecutionResult:
    scan_id: str
    scheduled_at: datetime
    processed: int
    trade_ready: int
    rejected_or_invalidated: int
    status: str = "COMPLETED"


class StaticScanPlanProvider:
    """Deterministic scan-plan source for tests and local development.

    Production discovery engines can implement ScanPlanProvider without changing
    the worker or qualification boundary.
    """

    def __init__(self, plans: Mapping[str, Sequence[QualificationRequest]]) -> None:
        self._plans = {scan_id: tuple(requests) for scan_id, requests in plans.items()}

    def requests(self, scan_id: str, scheduled_at: datetime) -> Sequence[QualificationRequest]:
        return self._plans.get(scan_id, ())


class ScanExecutorService:
    """Execute one scheduled scan through provider, validation and qualification.

    This layer owns scan-level persistence. It deliberately does not place broker
    orders and does not contain market-data strategy logic.
    """

    def __init__(
        self,
        *,
        plan_provider: ScanPlanProvider | Callable[[str, datetime], Sequence[QualificationRequest]],
        qualification: QualificationService,
        candidate_store: PersistentCandidateStore,
        learning_store: PersistentLearningStore,
        audit_store: PersistentAuditStore,
        equity: float,
        current_heat: float = 0.0,
        daily_loss: float = 0.0,
        exceptional: bool = False,
        max_age_seconds: float = 30.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.plan_provider = plan_provider
        self.qualification = qualification
        self.candidate_store = candidate_store
        self.learning_store = learning_store
        self.audit_store = audit_store
        self.equity = equity
        self.current_heat = current_heat
        self.daily_loss = daily_loss
        self.exceptional = exceptional
        self.max_age_seconds = max_age_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def execute(self, scan_id: str, scheduled_at: datetime) -> ScanExecutionResult:
        requests = self._requests(scan_id, scheduled_at)
        processed = 0
        trade_ready = 0
        rejected_or_invalidated = 0
        execution_time = self.clock()

        if not requests:
            self.audit_store.append(self._no_plan_event(scan_id, scheduled_at, execution_time))
            return ScanExecutionResult(
                scan_id=scan_id,
                scheduled_at=scheduled_at,
                processed=0,
                trade_ready=0,
                rejected_or_invalidated=0,
                status="NO_PLAN",
            )

        for request in requests:
            result = self.qualification.qualify(
                request,
                equity=self.equity,
                now=execution_time,
                current_heat=self.current_heat,
                daily_loss=self.daily_loss,
                exceptional=self.exceptional,
                max_age_seconds=self.max_age_seconds,
            )
            candidate = self.candidate_store.upsert(result.candidate)
            record = LearningRecord(
                symbol=candidate.symbol,
                discovered_at=candidate.discovered_at,
                discovery_score=candidate.score,
                discovery_state=candidate.state,
                trigger_confirmed=request.trigger_confirmed,
                trade_ready=result.risk_decision.approved if result.risk_decision else False,
                reasons=list(result.execution_reasons) + list(candidate.rejection_reasons),
            )
            self.learning_store.create(record)
            self.audit_store.append(
                self._candidate_event(
                    candidate.symbol,
                    candidate.state.value,
                    scan_id=scan_id,
                    scheduled_at=scheduled_at.isoformat(),
                    evaluated_at=execution_time.isoformat(),
                    score=candidate.score,
                    trade_ready=record.trade_ready,
                    reasons=record.reasons,
                    discovery_source=request.discovery_source,
                    discovery_evidence=list(request.discovery_evidence),
                )
            )
            processed += 1
            if record.trade_ready:
                trade_ready += 1
            else:
                rejected_or_invalidated += 1

        return ScanExecutionResult(
            scan_id=scan_id,
            scheduled_at=scheduled_at,
            processed=processed,
            trade_ready=trade_ready,
            rejected_or_invalidated=rejected_or_invalidated,
        )

    def _requests(self, scan_id: str, scheduled_at: datetime) -> Sequence[QualificationRequest]:
        provider = self.plan_provider
        if hasattr(provider, "requests"):
            return provider.requests(scan_id, scheduled_at)  # type: ignore[attr-defined]
        return provider(scan_id, scheduled_at)  # type: ignore[operator]

    @staticmethod
    def _candidate_event(symbol: str, state: str, **payload: object):
        from .ledger import AuditEvent

        scheduled_at = str(payload.pop("scheduled_at"))
        return AuditEvent(
            event_type="CANDIDATE_QUALIFIED",
            symbol=symbol,
            timestamp=datetime.fromisoformat(scheduled_at),
            state=state,
            payload=payload,
        )

    @staticmethod
    def _no_plan_event(scan_id: str, scheduled_at: datetime, evaluated_at: datetime):
        from .ledger import AuditEvent

        return AuditEvent(
            event_type="SCAN_NO_PLAN",
            symbol=None,
            timestamp=evaluated_at,
            payload={
                "scan_id": scan_id,
                "scheduled_at": scheduled_at.isoformat(),
                "evaluated_at": evaluated_at.isoformat(),
                "reason": "scan plan provider returned no requests",
            },
        )
