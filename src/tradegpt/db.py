from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, create_engine
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


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///tradegpt.db")


def make_engine(url: str | None = None):
    return create_engine(url or database_url(), pool_pre_ping=True)


def init_db(engine=None) -> None:
    engine = engine or make_engine()
    Base.metadata.create_all(engine)


def make_session_factory(engine=None):
    return sessionmaker(bind=engine or make_engine(), expire_on_commit=False)
