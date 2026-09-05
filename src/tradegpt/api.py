from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

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


def candidate_payload(candidate: Candidate) -> dict:
    payload = asdict(candidate)
    payload["state"] = candidate.state.value
    payload["discovered_at"] = candidate.discovered_at.isoformat()
    return payload
