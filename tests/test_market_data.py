from datetime import datetime, timedelta, timezone

import pytest

from tradegpt.market_data import QuoteSnapshot, unverified_snapshot, validate_snapshot


def valid_snapshot(*, timestamp: datetime | None = None, **overrides: object) -> QuoteSnapshot:
    values: dict[str, object] = {
        "symbol": "aapl",
        "timestamp": timestamp or datetime.now(timezone.utc),
        "last_price": 100.0,
        "vwap": 99.5,
        "rvol": 2.1,
        "relative_strength": 1.08,
        "adv_shares": 1_000_000.0,
        "adv_dollars": 100_000_000.0,
        "verified": True,
        "source": "test-provider",
        "latency_ms": 42.0,
    }
    values.update(overrides)
    return QuoteSnapshot(**values)  # type: ignore[arg-type]


def test_fresh_complete_snapshot_is_verified() -> None:
    now = datetime.now(timezone.utc)
    result = validate_snapshot(valid_snapshot(timestamp=now - timedelta(seconds=5)), now=now)
    assert result.verified is True
    assert result.data_status == "VERIFIED"
    assert result.symbol == "AAPL"
    assert result.verification_reasons == ()


def test_stale_snapshot_fails_closed() -> None:
    now = datetime.now(timezone.utc)
    result = validate_snapshot(valid_snapshot(timestamp=now - timedelta(seconds=31)), now=now)
    assert result.verified is False
    assert result.data_status == "DATA_NOT_VERIFIED"
    assert any(reason.startswith("STALE_DATA:") for reason in result.verification_reasons)


def test_missing_required_field_fails_closed() -> None:
    now = datetime.now(timezone.utc)
    result = validate_snapshot(valid_snapshot(timestamp=now, vwap=None), now=now)
    assert result.verified is False
    assert "MISSING_VWAP" in result.verification_reasons


def test_naive_timestamp_fails_closed() -> None:
    naive = datetime.now()
    now = datetime.now(timezone.utc)
    result = validate_snapshot(valid_snapshot(timestamp=naive), now=now)
    assert result.verified is False
    assert "TIMESTAMP_MUST_BE_TIMEZONE_AWARE" in result.verification_reasons


def test_future_timestamp_fails_closed() -> None:
    now = datetime.now(timezone.utc)
    result = validate_snapshot(valid_snapshot(timestamp=now + timedelta(seconds=1)), now=now)
    assert result.verified is False
    assert "TIMESTAMP_IN_FUTURE" in result.verification_reasons


def test_invalid_price_fails_closed() -> None:
    now = datetime.now(timezone.utc)
    result = validate_snapshot(valid_snapshot(timestamp=now, last_price=0), now=now)
    assert result.verified is False
    assert "INVALID_LAST_PRICE" in result.verification_reasons


@pytest.mark.parametrize("field", ["rvol", "relative_strength", "adv_shares", "adv_dollars", "last_price"])
def test_missing_market_field_fails_closed(field: str) -> None:
    now = datetime.now(timezone.utc)
    result = validate_snapshot(valid_snapshot(timestamp=now, **{field: None}), now=now)
    assert result.verified is False
    assert f"MISSING_{field.upper()}" in result.verification_reasons


def test_source_and_latency_are_preserved() -> None:
    now = datetime.now(timezone.utc)
    result = validate_snapshot(valid_snapshot(timestamp=now, source="polygon", latency_ms=17.5), now=now)
    assert result.source == "polygon"
    assert result.latency_ms == 17.5


def test_already_unverified_snapshot_cannot_be_promoted() -> None:
    now = datetime.now(timezone.utc)
    snapshot = valid_snapshot(timestamp=now, verified=False)
    result = validate_snapshot(snapshot, now=now)
    assert result.verified is False


def test_custom_max_age_is_respected() -> None:
    now = datetime.now(timezone.utc)
    snapshot = valid_snapshot(timestamp=now - timedelta(seconds=11))
    result = validate_snapshot(snapshot, now=now, max_age_seconds=10)
    assert result.verified is False
    assert any(reason.startswith("STALE_DATA:") for reason in result.verification_reasons)


def test_unverified_snapshot_preserves_source() -> None:
    now = datetime.now(timezone.utc)
    snapshot = unverified_snapshot("msft", now, "provider unavailable", source="alpaca")
    assert snapshot.source == "alpaca"
    assert snapshot.verified is False
    assert snapshot.last_price is None
