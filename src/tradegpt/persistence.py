from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from .db import AuditEventRow, CandidateRow, LearningRecordRow, make_session_factory
from .ledger import AuditEvent
from .learning import LearningRecord, Outcome
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


class PersistentAuditStore:
    """Durable append-only audit-event repository."""

    def __init__(self, session_factory=None) -> None:
        self.session_factory = session_factory or make_session_factory()

    def append(self, event: AuditEvent) -> AuditEvent:
        with self.session_factory() as session:
            row = AuditEventRow(
                timestamp=event.timestamp,
                event_type=event.event_type,
                symbol=event.symbol.upper(),
                payload=json.dumps({"state": event.state, **event.payload}),
            )
            session.add(row)
            session.commit()
        return event

    def for_symbol(self, symbol: str) -> list[AuditEvent]:
        with self.session_factory() as session:
            stmt = select(AuditEventRow).where(AuditEventRow.symbol == symbol.upper()).order_by(AuditEventRow.id)
            return [self._to_model(row) for row in session.scalars(stmt)]

    @staticmethod
    def _to_model(row: AuditEventRow) -> AuditEvent:
        payload = json.loads(row.payload or "{}")
        state = payload.pop("state", None)
        return AuditEvent(
            event_type=row.event_type,
            symbol=row.symbol,
            timestamp=row.timestamp,
            state=state,
            payload=payload,
        )


class PersistentLearningStore:
    """Durable forward-test learning repository."""

    def __init__(self, session_factory=None) -> None:
        self.session_factory = session_factory or make_session_factory()

    def create(self, record: LearningRecord) -> int:
        with self.session_factory() as session:
            row = LearningRecordRow(
                symbol=record.symbol.upper(),
                discovered_at=record.discovered_at,
                discovery_score=record.discovery_score,
                discovery_state=record.discovery_state.value,
                trigger_confirmed=record.trigger_confirmed,
                trade_ready=record.trade_ready,
                traded=record.traded,
                missed_opportunity=record.missed_opportunity,
                reasons=json.dumps(record.reasons),
            )
            session.add(row)
            session.commit()
            return row.id

    def update(self, record_id: int, record: LearningRecord) -> None:
        with self.session_factory() as session:
            row = session.get(LearningRecordRow, record_id)
            if row is None:
                raise KeyError(f"learning record {record_id} not found")
            row.trigger_confirmed = record.trigger_confirmed
            row.trade_ready = record.trade_ready
            row.traded = record.traded
            row.missed_opportunity = record.missed_opportunity
            row.reasons = json.dumps(record.reasons)
            if record.outcome is not None:
                outcome = record.outcome
                row.evaluated_at = outcome.evaluated_at
                row.entry_price = outcome.entry_price
                row.exit_price = outcome.exit_price
                row.stop_price = outcome.stop_price
                row.target_price = outcome.target_price
                row.outcome_r = outcome.outcome_r
                row.max_adverse_excursion_r = outcome.max_adverse_excursion_r
                row.max_favorable_excursion_r = outcome.max_favorable_excursion_r
                row.result = outcome.result
            session.commit()

    def get(self, record_id: int) -> LearningRecord | None:
        with self.session_factory() as session:
            row = session.get(LearningRecordRow, record_id)
            return self._to_model(row) if row else None

    def list(self, symbol: str | None = None) -> list[LearningRecord]:
        with self.session_factory() as session:
            stmt = select(LearningRecordRow).order_by(LearningRecordRow.id.asc())
            if symbol:
                stmt = stmt.where(LearningRecordRow.symbol == symbol.upper())
            return [self._to_model(row) for row in session.scalars(stmt)]

    @staticmethod
    def _to_model(row: LearningRecordRow) -> LearningRecord:
        record = LearningRecord(
            symbol=row.symbol,
            discovered_at=row.discovered_at,
            discovery_score=row.discovery_score,
            discovery_state=CandidateState(row.discovery_state),
            trigger_confirmed=row.trigger_confirmed,
            trade_ready=row.trade_ready,
            traded=row.traded,
            missed_opportunity=row.missed_opportunity,
            reasons=json.loads(row.reasons or "[]"),
        )
        if row.evaluated_at is not None:
            record.outcome = Outcome(
                symbol=row.symbol,
                evaluated_at=row.evaluated_at,
                entry_price=row.entry_price,
                exit_price=row.exit_price,
                stop_price=row.stop_price,
                target_price=row.target_price,
                outcome_r=row.outcome_r,
                max_adverse_excursion_r=row.max_adverse_excursion_r,
                max_favorable_excursion_r=row.max_favorable_excursion_r,
                result=row.result,
            )
        return record
