from __future__ import annotations

import os

from .configured import ConfiguredMarketDataProvider
from .http import HttpSnapshotConfig, HttpSnapshotProvider


def _positive_float(value: str | None, default: float = 5.0) -> float:
    if value is None or not value.strip():
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    if parsed <= 0:
        return default
    return min(parsed, 30.0)


def build_market_data_provider(*, environ: dict[str, str] | None = None) -> ConfiguredMarketDataProvider:
    """Build the production market-data boundary from environment configuration.

    No vendor is selected by default. Unsupported or incomplete configuration
    remains fail-closed and produces unverified snapshots rather than synthetic data.
    """
    env = environ if environ is not None else os.environ
    provider = env.get("MARKET_DATA_PROVIDER", "none").strip().lower() or "none"

    if provider == "none":
        return ConfiguredMarketDataProvider(None, provider_name="none")

    if provider != "http":
        return ConfiguredMarketDataProvider(None, provider_name=f"unsupported:{provider}")

    base_url = env.get("MARKET_DATA_BASE_URL", "").strip()
    if not base_url:
        return ConfiguredMarketDataProvider(None, provider_name="http:missing_base_url")

    api_key_env = env.get("MARKET_DATA_API_KEY_ENV", "").strip() or None
    timeout = _positive_float(env.get("MARKET_DATA_TIMEOUT_SECONDS"), 5.0)
    client = HttpSnapshotProvider(
        HttpSnapshotConfig(
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout,
        ),
        environ=env,
    )
    return ConfiguredMarketDataProvider(client, provider_name="http")
