from datetime import datetime, timezone

from tradegpt.db import init_db, make_engine, make_session_factory
from tradegpt.market_data import QuoteSnapshot
from tradegpt.persistence import PersistentAuditStore, PersistentCandidateStore, PersistentLearningStore
from tradegpt.qualification import QualificationRequest, QualificationService, StaticProvider
from tradegpt.scan_executor import ScanExecutorService, StaticScanPlanProvider


NOW = datetime(2026, 9, 7, 14, 15, tzinfo=timezone.utc)


def _stores():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    return (
        PersistentCandidateStore(factory),
        PersistentLearningStore(factory),
        PersistentAuditStore(factory),
    )


def _request(symbol: str = "TEST") -> QualificationRequest:
    return QualificationRequest(
        symbol=symbol,
        catalyst_score=100,
        technical_score=100,
        relative_strength_score=100,
        liquidity_score=100,
        entry_trigger=20,
        stop_price=19,
        target_price=22,
        trigger_confirmed=True,
    )


def _snapshot(*, timestamp=NOW, verified=True) -> QuoteSnapshot:
    return QuoteSnapshot(
        symbol="TEST",
        timestamp=timestamp,
        last_price=20,
        vwap=19.5,
        rvol=2.5,
        relative_strength=90,
        adv_shares=1_000_000,
        adv_dollars=20_000_000,
        verified=verified,
        verification_reasons=() if verified else ("provider marked unverified",),
        source="test",
        latency_ms=5,
    )


def test_executor_qualifies_and_persists_trade_ready_candidate():
    candidates, learning, audit = _stores()
    qualification = QualificationService(StaticProvider(_snapshot()))
    executor = ScanExecutorService(
        plan_provider=StaticScanPlanProvider({"daily-discovery": (_request(),)}),
        qualification=qualification,
        candidate_store=candidates,
        learning_store=learning,
        audit_store=audit,
        equity=2905,
        clock=lambda: NOW,
    )

    result = executor.execute("daily-discovery", NOW)

    assert result.processed == 1
    assert result.trade_ready == 1
    assert result.status == "COMPLETED"
    candidate = candidates.get("TEST")
    assert candidate is not None
    assert candidate.state.value == "TRADE_READY"
    assert learning.list("TEST")[0].trade_ready is True
    assert audit.list("CANDIDATE_QUALIFIED")[0].payload["scan_id"] == "daily-discovery"


def test_executor_reports_no_plan_instead_of_false_completion():
    candidates, learning, audit = _stores()
    qualification = QualificationService(StaticProvider(_snapshot()))
    executor = ScanExecutorService(
        plan_provider=StaticScanPlanProvider({}),
        qualification=qualification,
        candidate_store=candidates,
        learning_store=learning,
        audit_store=audit,
        equity=2905,
        clock=lambda: NOW,
    )

    result = executor.execute("daily-discovery", NOW)

    assert result.status == "NO_PLAN"
    assert result.processed == 0
    assert candidates.get("TEST") is None
    assert learning.list() == []
    events = audit.list()
    assert [event.event_type for event in events] == ["SCAN_NO_PLAN"]
    assert events[0].payload["scan_id"] == "daily-discovery"


def test_executor_fail_closed_on_stale_provider_data():
    candidates, learning, audit = _stores()
    stale = datetime(2026, 9, 7, 13, 0, tzinfo=timezone.utc)
    qualification = QualificationService(StaticProvider(_snapshot(timestamp=stale)))
    executor = ScanExecutorService(
        plan_provider=StaticScanPlanProvider({"primary-qualification": (_request(),)}),
        qualification=qualification,
        candidate_store=candidates,
        learning_store=learning,
        audit_store=audit,
        equity=2905,
        clock=lambda: NOW,
    )

    result = executor.execute("primary-qualification", NOW)

    assert result.processed == 1
    assert result.trade_ready == 0
    assert candidates.get("TEST").data_verified is False
    assert learning.list("TEST")[0].trade_ready is False


def test_executor_uses_each_scan_plan_without_strategy_logic_in_worker():
    candidates, learning, audit = _stores()
    qualification = QualificationService(StaticProvider(_snapshot()))
    calls = []

    def plan(scan_id, scheduled_at):
        calls.append((scan_id, scheduled_at))
        return (_request("TEST"),) if scan_id == "midday-discovery" else ()

    executor = ScanExecutorService(
        plan_provider=plan,
        qualification=qualification,
        candidate_store=candidates,
        learning_store=learning,
        audit_store=audit,
        equity=2905,
        clock=lambda: NOW,
    )

    result = executor.execute("midday-discovery", NOW)

    assert calls == [("midday-discovery", NOW)]
    assert result.processed == 1
    assert len(learning.list("TEST")) == 1
