from __future__ import annotations

import json
from datetime import datetime, timezone

from .db import AuditEventRow, make_session_factory
from .ledger import AuditEvent


class PersistentAuditStore:
    """Durable audit-event repository for state and decision history."""

    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory or make_session_factory()

    def append(self, event: AuditEvent) -> None:
        with self._session_factory() as session:
            session.add(
                AuditEventRow(
                    timestamp=event.timestamp,
                    event_type=event.event_type,
                    symbol=event.symbol,
                    payload=json.dumps(event.payload, sort_keys=True, default=str),
                )
            )
            session.commit()

    def list(self, symbol: str | None = None) -> list[AuditEvent]:
        with self._session_factory() as session:
            query = session.query(AuditEventRow).order_by(AuditEventRow.id.asc())
            if symbol:
                query = query.filter(AuditEventRow.symbol == symbol.upper())
            rows = query.all()
            return [
                AuditEvent(
                    event_type=row.event_type,
                    symbol=row.symbol,
                    timestamp=row.timestamp or datetime.now(timezone.utc),
                    payload=json.loads(row.payload or "{}"),
                )
                for row in rows
            ]
