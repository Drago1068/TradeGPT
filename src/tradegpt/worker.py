from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from .scheduler import ScanSchedule
from .scheduler_service import SchedulerService
from .scan_executor import ScanExecutionResult


class ScanExecutor(Protocol):
    def execute(self, scan_id: str, scheduled_at: datetime) -> ScanExecutionResult | None: ...


@dataclass(frozen=True)
class WorkerResult:
    scan_id: str
    scheduled_at: datetime
    status: str
    error: str | None = None


class SchedulerWorker:
    """One-shot scheduler worker boundary.

    The worker owns invocation/audit lifecycle only. Market-data acquisition and
    scan qualification remain behind the ScanExecutor boundary. It is designed
    to be called repeatedly by a process supervisor or timer and is safe against
    duplicate completed/failed/missed runs through SchedulerService's durable
    audit state.
    """

    def __init__(self, scheduler: SchedulerService, executor: ScanExecutor | Callable[[str, datetime], ScanExecutionResult | None]):
        self.scheduler = scheduler
        self.executor = executor

    def run_due(self, now: datetime | None = None) -> tuple[WorkerResult, ...]:
        moment = now if now is not None else datetime.now(timezone.utc)
        results: list[WorkerResult] = []
        for schedule in self.scheduler.due(moment):
            results.append(self.run_one(schedule, self.scheduler.scheduled_at(schedule.id, moment)))
        return tuple(results)

    def run_one(self, schedule: ScanSchedule, scheduled_at: datetime) -> WorkerResult:
        started_at = datetime.now(timezone.utc)
        run = self.scheduler.start(schedule.id, scheduled_at, started_at)
        try:
            if hasattr(self.executor, "execute"):
                result = self.executor.execute(schedule.id, scheduled_at)  # type: ignore[attr-defined]
            else:
                result = self.executor(schedule.id, scheduled_at)  # type: ignore[operator]
        except Exception as exc:
            failed = self.scheduler.fail(run, f"{type(exc).__name__}: {exc}")
            return WorkerResult(failed.scan_id, failed.scheduled_at, failed.status, failed.error)

        if isinstance(result, ScanExecutionResult) and result.status != "COMPLETED":
            terminal = self.scheduler.record_non_success(run, result.status, result.processed)
            return WorkerResult(terminal.scan_id, terminal.scheduled_at, terminal.status)

        completed = self.scheduler.complete(run)
        return WorkerResult(completed.scan_id, completed.scheduled_at, completed.status)
