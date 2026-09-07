from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from .db import Base
from .ledger import AuditLedger
from .models import Candidate, CandidateState


class CandidateStore:
    """Minimal repository abstraction; database-backed implementation can replace this without changing API contracts."""

    def __init__(self) -> None:
        self._items: dict[str, Candidate] = {}

    def upsert(self, candidate: Candidate) -> Candidate:
        self._items[candidate.symbol] = candidate
        return candidate

    def get(self, symbol: str) -> Candidate | None:
        return self._items.get(symbol.upper())

    def list(self, state: CandidateState | None = None) -> list[Candidate]:
        items = list(self._items.values())
        if state is not None:
            items = [item for item in items if item.state is state]
        return sorted(items, key=lambda item: item.score, reverse=True)


def health_payload() -> dict[str, str]:
    return {"status": "ok", "service": "tradegpt-v2", "timestamp": datetime.now(timezone.utc).isoformat()}


def readiness_payload(*, engine, market_data_configured: bool, scan_plan_configured: bool) -> tuple[dict[str, object], bool]:
    """Return operational readiness separately from process liveness."""
    checks: dict[str, dict[str, object]] = {
        "database": {"ready": False},
        "schema": {"ready": False},
        "market_data": {"ready": market_data_configured},
        "scan_plan": {"ready": scan_plan_configured},
    }
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"]["ready"] = True
    except Exception as exc:
        checks["database"]["error"] = f"{type(exc).__name__}: {exc}"

    if checks["database"]["ready"]:
        try:
            tables = set(inspect(engine).get_table_names())
            required = {table.name for table in Base.metadata.sorted_tables}
            checks["schema"]["ready"] = required.issubset(tables)
            if not checks["schema"]["ready"]:
                checks["schema"]["missing_tables"] = sorted(required - tables)
        except Exception as exc:
            checks["schema"]["error"] = f"{type(exc).__name__}: {exc}"

    ready = all(bool(check["ready"]) for check in checks.values())
    return {
        "status": "ready" if ready else "not_ready",
        "service": "tradegpt-v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }, ready


def candidate_payload(candidate: Candidate) -> dict:
    payload = asdict(candidate)
    payload["state"] = candidate.state.value
    payload["discovered_at"] = candidate.discovered_at.isoformat()
    return payload
