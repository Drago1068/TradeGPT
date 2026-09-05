from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    symbol: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class AuditLedger:
    """In-memory audit ledger; persistence is supplied by the database layer later."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def record(self, event_type: str, symbol: str, *, state: str | None = None, **payload: Any) -> AuditEvent:
        event = AuditEvent(event_type=event_type, symbol=symbol, state=state, payload=payload)
        self.append(event)
        return event

    def for_symbol(self, symbol: str) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self._events if e.symbol == symbol)

    def all(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)
