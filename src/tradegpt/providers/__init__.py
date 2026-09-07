"""External market-data provider adapters and failover boundaries."""

from .base import MarketDataProviderError, ProviderUnavailable
from .configured import ConfiguredMarketDataProvider

__all__ = ["ConfiguredMarketDataProvider", "MarketDataProviderError", "ProviderUnavailable"]
