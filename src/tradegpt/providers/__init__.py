"""External market-data provider adapters and failover boundaries."""

from .base import MarketDataProviderError, ProviderUnavailable
from .configured import ConfiguredMarketDataProvider
from .http import HttpSnapshotConfig, HttpSnapshotProvider

__all__ = [
    "ConfiguredMarketDataProvider",
    "HttpSnapshotConfig",
    "HttpSnapshotProvider",
    "MarketDataProviderError",
    "ProviderUnavailable",
]
