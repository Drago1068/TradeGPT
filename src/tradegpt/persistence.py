from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from .db import CandidateRow, make_session_factory
from .models import Candidate, CandidateState


class PersistentCandidateStore:
    """PostgreSQL/SQLAlchemy candidate repository with deterministic symbol identity."""

    def __init__(self, session_factory=None) -> None:
        self.session_factory = session_factory or make_session_factory()

    def upsert(self, candidate: Candidate) -> Candidate:
        symbol = candidate.symbol.upper()
        with self.session_factory() as session:
            row = session.get(CandidateRow, symbol)
            if row is None:
                row = CandidateRow(symbol=symbol)
                session.add(row)
            row.discovered_at = candidate.discovered_at
            row.state = candidate.state.value
            row.score = candidate.score
            row.catalyst_score = candidate.catalyst_score
            row.technical_score = candidate.technical_score
            row.relative_strength_score = candidate.relative_strength_score
            row.liquidity_score = candidate.liquidity_score
            row.entry_trigger = candidate.entry_trigger
            row.stop_price = candidate.stop_price
            row.target_price = candidate.target_price
            row.last_price = candidate.last_price
            row.data_verified = candidate.data_verified
            row.rejection_reasons = json.dumps(candidate.rejection_reasons)
            session.commit()
        return candidate

    def get(self, symbol: str) -> Candidate | None:
        with self.session_factory() as session:
            row = session.get(CandidateRow, symbol.upper())
            return self._to_model(row) if row else None

    def list(self, state: CandidateState | None = None) -> list[Candidate]:
        with self.session_factory() as session:
            stmt = select(CandidateRow).order_by(CandidateRow.score.desc())
            if state is not None:
                stmt = stmt.where(CandidateRow.state == state.value)
            return [self._to_model(row) for row in session.scalars(stmt)]

    @staticmethod
    def _to_model(row: CandidateRow) -> Candidate:
        try:
            reasons = json.loads(row.rejection_reasons or "[]")
        except json.JSONDecodeError:
            reasons = []
        return Candidate(
            symbol=row.symbol,
            discovered_at=row.discovered_at,
            state=CandidateState(row.state),
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
            rejection_reasons=reasons,
        )
