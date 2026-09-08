from datetime import datetime, timezone

from tradegpt.db import init_db, make_engine, make_session_factory
from tradegpt.market_data import QuoteSnapshot
from tradegpt.models import Candidate, CandidateState
from tradegpt.observation import ScanObservation
from tradegpt.observation_persistence import PersistentScanObservationStore
from tradegpt.persistence import PersistentCandidateStore, PersistentAuditStore, PersistentLearningStore
from tradegpt.qualification import QualificationRequest, QualificationService, StaticProvider
from tradegpt.scan_executor import ScanExecutorService, StaticScanPlanProvider


NOW = datetime(2026, 9, 8, 13, 15, tzinfo=timezone.utc)


def _candidate_store_graph():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    return engine, PersistentCandidateStore(factory), PersistentLearningStore(factory), PersistentAuditStore(factory), PersistentScanObservationStore(factory)


def _request():
    return QualificationRequest(
        symbol="TEST",
        catalyst_score=100,
        technical_score=100,
        relative_strength_score=100,
        liquidity_score=100,
        entry_trigger=20,
        stop_price=19,
        target_price=22,
        trigger_confirmed=True,
        discovery_source="QWEN",
        discovery_evidence=("fresh catalyst", "relative volume"),
    )


def _snapshot():
    return QuoteSnapshot(
        symbol="TEST", timestamp=NOW, last_price=20, vwap=19.5, rvol=2.5,
        relative_strength=90, adv_shares=1_000_000, adv_dollars=20_000_000,
        verified=True, verification_reasons=(), source="test", latency_ms=5,
    )


def test_scan_observation_is_append_only_across_scans():
    _, candidates, learning, audit, observations = _candidate_store_graph()
    executor = ScanExecutorService(
        plan_provider=StaticScanPlanProvider({"daily-sniper-discovery": (_request(),)}),
        qualification=QualificationService(StaticProvider(_snapshot())),
        candidate_store=candidates,
        learning_store=learning,
        audit_store=audit,
        observation_store=observations,
        equity=2905,
        clock=lambda: NOW,
    )

    executor.execute("daily-sniper-discovery", NOW)
    later = NOW.replace(hour=14, minute=15)
    executor.execute("daily-sniper-discovery", later)

    rows = observations.list(symbol="TEST")
    assert len(rows) == 2
    assert rows[0].scheduled_at == NOW
    assert rows[1].scheduled_at == later
    assert rows[0].discovery_source == "QWEN"
    assert rows[0].candidate.state == CandidateState.TRADE_READY


def test_same_scan_retry_is_idempotent_at_observation_key():
    _, _, _, _, observations = _candidate_store_graph()
    candidate = Candidate(
        symbol="TEST", discovered_at=NOW, state=CandidateState.TRADE_READY,
        score=95, catalyst_score=100, technical_score=95,
        relative_strength_score=90, liquidity_score=100,
        entry_trigger=20, stop_price=19, target_price=22,
        last_price=20, data_verified=True, rejection_reasons=[],
    )
    observation = ScanObservation("daily-sniper-discovery", NOW, NOW, candidate, "QWEN", ("catalyst",))
    first_id = observations.create(observation)
    second_id = observations.create(observation)
    assert second_id == first_id
    assert len(observations.list(scan_id="daily-sniper-discovery", symbol="TEST")) == 1
