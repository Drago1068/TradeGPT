from datetime import datetime, timezone

from tradegpt.scan_executor import ScanExecutorService


SCHEDULED = datetime(2026, 9, 8, 13, 0, tzinfo=timezone.utc)
EVALUATED = datetime(2026, 9, 8, 13, 15, tzinfo=timezone.utc)


def test_candidate_audit_event_uses_evaluation_timestamp_not_scheduled_timestamp():
    event = ScanExecutorService._candidate_event(
        "TEST",
        "TRADE_READY",
        scan_id="daily-sniper-discovery",
        scheduled_at=SCHEDULED.isoformat(),
        evaluated_at=EVALUATED.isoformat(),
        score=95.0,
        trade_ready=True,
        reasons=[],
    )

    assert event.timestamp == EVALUATED
    assert event.payload["scan_id"] == "daily-sniper-discovery"
