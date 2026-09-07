from datetime import datetime, timezone

import pytest

from tradegpt.market_data import QuoteSnapshot
from tradegpt.providers import ConfiguredMarketDataProvider, ProviderUnavailable
from tradegpt.providers.base import fetch_verified_snapshot


def make_snapshot() -> QuoteSnapshot:
    return QuoteSnapshot(
        symbol="AAPL", timestamp=datetime.now(timezone.utc), last_price=100.0,
        vwap=99.0, rvol=2.0, relative_strength=1.1,
        adv_shares=1_000_000, adv_dollars=100_000_000,
        verified=True, source="fixture",
    )


def test_missing_provider_fails_closed() -> None:
    result = ConfiguredMarketDataProvider(provider_name="test").snapshot("aapl")
    assert result.symbol == "AAPL"
    assert result.verified is False
    assert result.data_status == "DATA_NOT_VERIFIED"
    assert result.source == "test"
    assert "MARKET_DATA_PROVIDER_NOT_CONFIGURED" in result.verification_reasons


def test_configured_provider_normalizes_symbol() -> None:
    provider = ConfiguredMarketDataProvider(lambda _: make_snapshot(), provider_name="fixture")
    result = provider.snapshot("aapl")
    assert result.symbol == "AAPL"
    assert result.verified is True


def test_provider_exception_fails_closed() -> None:
    def broken(_: str) -> QuoteSnapshot:
        raise RuntimeError("network down")
    result = ConfiguredMarketDataProvider(broken, provider_name="fixture").snapshot("aapl")
    assert result.verified is False
    assert "provider fetch failed" in result.verification_reasons[0]


def test_invalid_provider_result_is_rejected() -> None:
    with pytest.raises(ProviderUnavailable):
        fetch_verified_snapshot(lambda _: "invalid", "aapl")  # type: ignore[arg-type]
