from __future__ import annotations

import json

from sqlalchemy import select

from .db import ScanObservationRow
from .models import Candidate
from .observation import ScanObservation


class PersistentScanObservationStore:
    """Append-only persistence for per-scan candidate observations."""

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def create(self, observation: ScanObservation) -> int:
        candidate = observation.candidate
        with self.session_factory() as session:
            row = ScanObservationRow(
                scan_id=observation.scan_id,
                scheduled_at=observation.scheduled_at,
                evaluated_at=observation.evaluated_at,
                symbol=candidate.symbol.upper(),
                state=candidate.state.value,
                score=candidate.score,
                catalyst_score=candidate.catalyst_score,
                technical_score=candidate.technical_score,
                relative_strength_score=candidate.relative_strength_score,
                liquidity_score=candidate.liquidity_score,
                entry_trigger=candidate.entry_trigger,
                stop_price=candidate.stop_price,
                target_price=candidate.target_price,
                last_price=candidate.last_price,
                data_verified=candidate.data_verified,
                rejection_reasons=json.dumps(candidate.rejection_reasons),
                discovery_source=observation.discovery_source,
                discovery_evidence=json.dumps(list(observation.discovery_evidence)),
            )
            session.add(row)
            session.commit()
            return row.id

    def list(self, scan_id: str | None = None, symbol: str | None = None) -> list[ScanObservation]:
        with self.session_factory() as session:
            stmt = select(ScanObservationRow).order_by(ScanObservationRow.id.asc())
            if scan_id:
                stmt = stmt.where(ScanObservationRow.scan_id == scan_id)
            if symbol:
                stmt = stmt.where(ScanObservationRow.symbol == symbol.upper())
            return [self._to_model(row) for row in session.scalars(stmt)]

    @staticmethod
    def _to_model(row: ScanObservationRow) -> ScanObservation:
        candidate = Candidate(
            symbol=row.symbol,
            discovered_at=row.evaluated_at,
            state=row.state,
            score=row.score,
            catalyst_score=row.catalyst_score,
            technical_score=row.technical_score,
            relative_strength_score=row.relative_strength_score,
            liquidity_score=row.liquidity_score,
            entry_trigger=row.entry_trigger,
            stop_price=row.stop_price,
            target_price=row.target_price,
            last_price=row.last_price,
            data_verified=row.data_verified,
            rejection_reasons=json.loads(row.rejection_reasons or "[]"),
        )
        from .models import CandidateState
        candidate.state = CandidateState(row.state)
        return ScanObservation(
            scan_id=row.scan_id,
            scheduled_at=row.scheduled_at,
            evaluated_at=row.evaluated_at,
            candidate=candidate,
            discovery_source=row.discovery_source,
            discovery_evidence=tuple(json.loads(row.discovery_evidence or "[]")),
        )
