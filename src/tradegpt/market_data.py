from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class QuoteSnapshot:
    symbol: str
    timestamp: datetime
    last_price: float | None
    vwap: float | None
    rvol: float | None
    relative_strength: float | None
    adv_shares: float | None
    adv_dollars: float | None
    verified: bool
    verification_reasons: tuple[str, ...] = ()

    @property
    def data_status(self) -> str:
        return "VERIFIED" if self.verified else "DATA_NOT_VERIFIED"


class MarketDataProvider(Protocol):
    """Provider boundary; concrete Polygon/Alpaca adapters belong outside strategy logic."""

    def snapshot(self, symbol: str) -> QuoteSnapshot: ...


def unverified_snapshot(symbol: str, timestamp: datetime, reason: str) -> QuoteSnapshot:
    """Create an explicit fail-closed snapshot when required data is unavailable."""
    return QuoteSnapshot(
        symbol=symbol.upper(),
        timestamp=timestamp,
        last_price=None,
        vwap=None,
        rvol=None,
        relative_strength=None,
        adv_shares=None,
        adv_dollars=None,
        verified=False,
        verification_reasons=(reason,),
    )
