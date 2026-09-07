from __future__ import annotations

from typing import Callable

from ..market_data import QuoteSnapshot


class MarketDataProviderError(RuntimeError):
    """Base error for provider failures; callers must fail closed."""


class ProviderUnavailable(MarketDataProviderError):
    """Raised when a configured provider cannot supply a usable snapshot."""


SnapshotFetcher = Callable[[str], QuoteSnapshot]


def fetch_verified_snapshot(
    fetcher: SnapshotFetcher,
    symbol: str,
) -> QuoteSnapshot:
    """Execute an adapter behind a narrow boundary and never hide provider errors."""
    try:
        snapshot = fetcher(symbol.upper())
    except MarketDataProviderError:
        raise
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise ProviderUnavailable(f"provider fetch failed for {symbol.upper()}") from exc

    if not isinstance(snapshot, QuoteSnapshot):
        raise ProviderUnavailable("provider returned an invalid snapshot type")
    return snapshot
