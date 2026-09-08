from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import URLError

import pytest

from tradegpt.market_data import validate_snapshot
from tradegpt.providers import HttpSnapshotConfig, HttpSnapshotProvider, ProviderUnavailable


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return self._body


def valid_payload() -> dict[str, object]:
    return {
        "timestamp": "2026-09-08T14:00:00+00:00",
        "last_price": 20.0,
        "vwap": 19.8,
        "rvol": 2.5,
        "relative_strength": 1.2,
        "adv_shares": 1_000_000,
        "adv_dollars": 20_000_000,
        "verified": True,
        "source": "test-provider",
        "latency_ms": 42.0,
    }


def test_valid_response_maps_to_verified_snapshot() -> None:
    seen: dict[str, object] = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["authorization"] = request.headers.get("Authorization")
        seen["timeout"] = timeout
        return FakeResponse(valid_payload())

    provider = HttpSnapshotProvider(
        HttpSnapshotConfig("https://data.example.test/v1", api_key_env="TEST_API_KEY"),
        environ={"TEST_API_KEY": "secret"},
        opener=opener,
    )

    snapshot = provider.snapshot(" aapl ")

    assert snapshot.symbol == "AAPL"
    assert snapshot.verified is True
    assert snapshot.last_price == 20.0
    assert snapshot.source == "test-provider"
    assert seen == {
        "url": "https://data.example.test/v1/AAPL",
        "authorization": "Bearer secret",
        "timeout": 5.0,
    }


def test_missing_credential_fails_closed() -> None:
    provider = HttpSnapshotProvider(
        HttpSnapshotConfig("https://data.example.test", api_key_env="TEST_API_KEY"),
        environ={},
        opener=lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )

    with pytest.raises(ProviderUnavailable, match="missing provider credential"):
        provider.snapshot("AAPL")


def test_timeout_or_network_failure_becomes_provider_unavailable() -> None:
    def opener(*_args, **_kwargs):
        raise URLError("connection refused")

    provider = HttpSnapshotProvider(HttpSnapshotConfig("https://data.example.test"), opener=opener)

    with pytest.raises(ProviderUnavailable, match="provider request failed"):
        provider.snapshot("AAPL")


def test_malformed_json_or_shape_becomes_provider_unavailable() -> None:
    class BadResponse(FakeResponse):
        def __init__(self):
            self._body = b"not-json"

    provider = HttpSnapshotProvider(
        HttpSnapshotConfig("https://data.example.test"),
        opener=lambda *_args, **_kwargs: BadResponse(),
    )

    with pytest.raises(ProviderUnavailable, match="provider request failed"):
        provider.snapshot("AAPL")

    provider = HttpSnapshotProvider(
        HttpSnapshotConfig("https://data.example.test"),
        opener=lambda *_args, **_kwargs: FakeResponse({"timestamp": "2026-09-08T14:00:00+00:00"}),
    )
    with pytest.raises(ProviderUnavailable, match="invalid snapshot"):
        provider.snapshot("AAPL")


def test_unverified_provider_payload_remains_data_not_verified() -> None:
    payload = valid_payload()
    payload["verified"] = False
    payload["verification_reasons"] = ["PROVIDER_MARKED_UNVERIFIED"]

    provider = HttpSnapshotProvider(
        HttpSnapshotConfig("https://data.example.test"),
        opener=lambda *_args, **_kwargs: FakeResponse(payload),
    )
    snapshot = provider.snapshot("AAPL")

    assert snapshot.verified is False
    assert snapshot.data_status == "DATA_NOT_VERIFIED"
    assert "PROVIDER_MARKED_UNVERIFIED" in snapshot.verification_reasons


def test_downstream_validation_fails_closed_for_bad_market_values() -> None:
    payload = valid_payload()
    payload["last_price"] = "NaN"

    provider = HttpSnapshotProvider(
        HttpSnapshotConfig("https://data.example.test"),
        opener=lambda *_args, **_kwargs: FakeResponse(payload),
    )
    snapshot = provider.snapshot("AAPL")
    validated = validate_snapshot(snapshot, now=datetime(2026, 9, 8, 14, 0, 1, tzinfo=timezone.utc))

    assert validated.verified is False
    assert "NON_FINITE_LAST_PRICE" in validated.verification_reasons
    assert validated.data_status == "DATA_NOT_VERIFIED"
