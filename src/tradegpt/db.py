from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class CandidateRow(Base):
    __tablename__ = "candidates"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    catalyst_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    technical_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    relative_strength_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    liquidity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    entry_trigger: Mapped[float | None] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)
    last_price: Mapped[float | None] = mapped_column(Float)
    data_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rejection_reasons: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ScanObservationRow(Base):
    __tablename__ = "scan_observations"
    __table_args__ = (UniqueConstraint("scan_id", "scheduled_at", "symbol", name="uq_scan_observation"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    catalyst_score: Mapped[float] = mapped_column(Float, nullable=False)
    technical_score: Mapped[float] = mapped_column(Float, nullable=False)
    relative_strength_score: Mapped[float] = mapped_column(Float, nullable=False)
    liquidity_score: Mapped[float] = mapped_column(Float, nullable=False)
    entry_trigger: Mapped[float | None] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)
    last_price: Mapped[float | None] = mapped_column(Float)
    data_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rejection_reasons: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    discovery_source: Mapped[str] = mapped_column(String(128), nullable=False, default="UNKNOWN")
    discovery_evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(16), nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class LearningRecordRow(Base):
    __tablename__ = "learning_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discovery_score: Mapped[float] = mapped_column(Float, nullable=False)
    discovery_state: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trade_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    traded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    missed_opportunity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasons: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[float | None] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)
    outcome_r: Mapped[float | None] = mapped_column(Float)
    max_adverse_excursion_r: Mapped[float | None] = mapped_column(Float)
    max_favorable_excursion_r: Mapped[float | None] = mapped_column(Float)
    result: Mapped[str] = mapped_column(String(32), nullable=False, default="UNRESOLVED")


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///tradegpt.db")


def make_engine(url: str | None = None):
    return create_engine(url or database_url(), pool_pre_ping=True)


def init_db(engine=None) -> None:
    engine = engine or make_engine()
    Base.metadata.create_all(engine)


def make_session_factory(engine=None):
    return sessionmaker(bind=engine or make_engine(), expire_on_commit=False)
