from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ForwardTestResult:
    outcome_r: float
    max_adverse_excursion_r: float
    max_favorable_excursion_r: float
    result: str


def evaluate_path(
    *,
    entry_price: float,
    stop_price: float,
    target_price: float,
    prices: Iterable[float],
) -> ForwardTestResult:
    """Evaluate a long trade path from sequential price observations.

    This evaluator deliberately does not infer intrabar ordering. For OHLC data,
    use an OHLC-specific evaluator before production because a bar can touch both
    stop and target and the sequence cannot be known from close prices alone.
    """
    if entry_price <= 0 or stop_price <= 0 or target_price <= 0:
        raise ValueError("prices must be positive")
    risk = entry_price - stop_price
    if risk <= 0:
        raise ValueError("stop_price must be below entry_price")
    if target_price <= entry_price:
        raise ValueError("target_price must be above entry_price")

    observations = list(prices)
    if not observations:
        raise ValueError("prices must contain at least one observation")
    if any(price <= 0 for price in observations):
        raise ValueError("observations must be positive")

    mae = min((price - entry_price) / risk for price in observations)
    mfe = max((price - entry_price) / risk for price in observations)

    for price in observations:
        if price <= stop_price:
            return ForwardTestResult(-1.0, mae, mfe, "STOPPED")
        if price >= target_price:
            return ForwardTestResult((target_price - entry_price) / risk, mae, mfe, "TARGET")

    last = observations[-1]
    return ForwardTestResult((last - entry_price) / risk, mae, mfe, "OPEN")
