"""External market-data provider adapters and failover boundaries."""

from .base import MarketDataProviderError, ProviderUnavailable
from .configured import ConfiguredMarketDataProvider
from .factory import build_market_data_provider
from .http import HttpSnapshotConfig, HttpSnapshotProvider

__all__ = [
    "ConfiguredMarketDataProvider",
    "HttpSnapshotConfig",
    "HttpSnapshotProvider",
    "MarketDataProviderError",
    "ProviderUnavailable",
    "build_market_data_provider",
]
