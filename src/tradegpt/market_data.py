from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
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
    source: str = "unknown"
    latency_ms: float | None = None

    @property
    def data_status(self) -> str:
        return "VERIFIED" if self.verified else "DATA_NOT_VERIFIED"


class MarketDataProvider(Protocol):
    """Provider boundary; concrete adapters stay outside strategy logic."""

    def snapshot(self, symbol: str) -> QuoteSnapshot: ...


def validate_snapshot(snapshot: QuoteSnapshot, *, now: datetime, max_age_seconds: float = 30.0) -> QuoteSnapshot:
    """Return a fail-closed snapshot when freshness or required fields are invalid.

    Numeric market inputs are also checked for finite, physically meaningful values.
    This prevents NaN/Infinity and negative volume metrics from reaching scoring or
    risk logic through an otherwise ``verified=True`` provider response.
    """
    reasons = list(snapshot.verification_reasons)
    symbol = snapshot.symbol.strip().upper()
    if not symbol:
        reasons.append("MISSING_SYMBOL")

    if snapshot.timestamp.tzinfo is None or now.tzinfo is None:
        reasons.append("TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    else:
        age = (now - snapshot.timestamp).total_seconds()
        if age < 0:
            reasons.append("TIMESTAMP_IN_FUTURE")
        elif age > max_age_seconds:
            reasons.append(f"STALE_DATA:{age:.1f}s")

    required = {
        "last_price": snapshot.last_price,
        "vwap": snapshot.vwap,
        "rvol": snapshot.rvol,
        "relative_strength": snapshot.relative_strength,
        "adv_shares": snapshot.adv_shares,
        "adv_dollars": snapshot.adv_dollars,
    }
    for field, value in required.items():
        if value is None:
            reasons.append(f"MISSING_{field.upper()}")
            continue
        if not isfinite(value):
            reasons.append(f"NON_FINITE_{field.upper()}")

    if snapshot.last_price is not None and isfinite(snapshot.last_price) and snapshot.last_price <= 0:
        reasons.append("INVALID_LAST_PRICE")
    if snapshot.vwap is not None and isfinite(snapshot.vwap) and snapshot.vwap <= 0:
        reasons.append("INVALID_VWAP")
    if snapshot.rvol is not None and isfinite(snapshot.rvol) and snapshot.rvol < 0:
        reasons.append("INVALID_RVOL")
    if snapshot.adv_shares is not None and isfinite(snapshot.adv_shares) and snapshot.adv_shares < 0:
        reasons.append("INVALID_ADV_SHARES")
    if snapshot.adv_dollars is not None and isfinite(snapshot.adv_dollars) and snapshot.adv_dollars < 0:
        reasons.append("INVALID_ADV_DOLLARS")
    if snapshot.latency_ms is not None and (not isfinite(snapshot.latency_ms) or snapshot.latency_ms < 0):
        reasons.append("INVALID_LATENCY_MS")

    verified = snapshot.verified and not reasons
    return QuoteSnapshot(
        symbol=symbol,
        timestamp=snapshot.timestamp,
        last_price=snapshot.last_price,
        vwap=snapshot.vwap,
        rvol=snapshot.rvol,
        relative_strength=snapshot.relative_strength,
        adv_shares=snapshot.adv_shares,
        adv_dollars=snapshot.adv_dollars,
        verified=verified,
        verification_reasons=tuple(dict.fromkeys(reasons)),
        source=snapshot.source,
        latency_ms=snapshot.latency_ms,
    )


def unverified_snapshot(symbol: str, timestamp: datetime, reason: str, *, source: str = "unknown") -> QuoteSnapshot:
    """Create an explicit fail-closed snapshot when required data is unavailable."""
    return QuoteSnapshot(
        symbol=symbol.upper(), timestamp=timestamp, last_price=None, vwap=None, rvol=None,
        relative_strength=None, adv_shares=None, adv_dollars=None, verified=False,
        verification_reasons=(reason,), source=source,
    )
