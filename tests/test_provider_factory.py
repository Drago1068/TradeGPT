from __future__ import annotations

from tradegpt.providers.factory import build_market_data_provider


def test_default_provider_is_safe_and_unconfigured() -> None:
    provider = build_market_data_provider(environ={})
    assert provider.is_configured is False
    assert provider.provider_name == "none"
    snapshot = provider.snapshot("AAPL")
    assert snapshot.verified is False
    assert "MARKET_DATA_PROVIDER_NOT_CONFIGURED" in snapshot.verification_reasons


def test_unsupported_provider_fails_closed() -> None:
    provider = build_market_data_provider(environ={"MARKET_DATA_PROVIDER": "polygon"})
    assert provider.is_configured is False
    assert provider.provider_name == "unsupported:polygon"


def test_http_without_base_url_fails_closed() -> None:
    provider = build_market_data_provider(environ={"MARKET_DATA_PROVIDER": "http"})
    assert provider.is_configured is False
    assert provider.provider_name == "http:missing_base_url"


def test_http_provider_is_configured_from_environment() -> None:
    provider = build_market_data_provider(
        environ={
            "MARKET_DATA_PROVIDER": "http",
            "MARKET_DATA_BASE_URL": "https://market.example.test/snapshot",
            "MARKET_DATA_API_KEY_ENV": "MARKET_API_KEY",
            "MARKET_DATA_TIMEOUT_SECONDS": "8",
            "MARKET_API_KEY": "test-secret",
        }
    )
    assert provider.is_configured is True
    assert provider.provider_name == "http"
    assert provider.fetcher.config.base_url == "https://market.example.test/snapshot"
    assert provider.fetcher.config.api_key_env == "MARKET_API_KEY"
    assert provider.fetcher.config.timeout_seconds == 8.0
