from datetime import datetime, timezone

from tradegpt.market_data import unverified_snapshot


def test_unverified_snapshot_fails_closed() -> None:
    snapshot = unverified_snapshot("aapl", datetime.now(timezone.utc), "quote feed unavailable")
    assert snapshot.symbol == "AAPL"
    assert snapshot.verified is False
    assert snapshot.data_status == "DATA_NOT_VERIFIED"
    assert snapshot.last_price is None
    assert snapshot.verification_reasons == ("quote feed unavailable",)
