from __future__ import annotations

import os
from datetime import datetime, timezone

from ..market_data import MarketDataProvider, QuoteSnapshot, unverified_snapshot
from .base import ProviderUnavailable, fetch_verified_snapshot


class ConfiguredMarketDataProvider:
    """Configuration boundary for real providers without embedding credentials."""

    def __init__(self, fetcher=None, *, provider_name: str | None = None) -> None:
        self.provider_name = provider_name or os.getenv("MARKET_DATA_PROVIDER", "none")
        self.fetcher = fetcher

    @property
    def is_configured(self) -> bool:
        """Whether a fetch implementation has been supplied to the adapter."""
        return self.fetcher is not None

    def snapshot(self, symbol: str) -> QuoteSnapshot:
        symbol = symbol.upper()
        if self.fetcher is None:
            return unverified_snapshot(
                symbol,
                datetime.now(timezone.utc),
                "MARKET_DATA_PROVIDER_NOT_CONFIGURED",
                source=self.provider_name,
            )
        try:
            return fetch_verified_snapshot(self.fetcher, symbol)
        except ProviderUnavailable as exc:
            return unverified_snapshot(symbol, datetime.now(timezone.utc), str(exc), source=self.provider_name)

    def as_provider(self) -> MarketDataProvider:
        """Expose only the provider protocol to strategy code."""
        return self
