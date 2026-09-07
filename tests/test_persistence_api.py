from datetime import datetime, timezone

from fastapi.testclient import TestClient

from tradegpt.app import app
from tradegpt.db import init_db, make_engine, make_session_factory
from tradegpt.learning import LearningLedger, Outcome
from tradegpt.models import Candidate, CandidateState
from tradegpt.persistence import PersistentCandidateStore, PersistentLearningStore


def test_persistent_store_round_trip(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'tradegpt.db'}")
    init_db(engine)
    store = PersistentCandidateStore(make_session_factory(engine))
    original = Candidate(
        symbol="TEST",
        discovered_at=datetime.now(timezone.utc),
        state=CandidateState.WATCH,
        score=84.5,
        data_verified=True,
    )
    store.upsert(original)
    restored = store.get("test")
    assert restored is not None
    assert restored.symbol == "TEST"
    assert restored.state is CandidateState.WATCH
    assert restored.score == 84.5


def test_persistent_learning_round_trip(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'learning.db'}")
    init_db(engine)
    store = PersistentLearningStore(make_session_factory(engine))
    now = datetime.now(timezone.utc)
    ledger = LearningLedger()
    record = ledger.record_discovery(
        symbol="TEST",
        discovered_at=now,
        score=94.0,
        state=CandidateState.TRADE_READY,
    )
    ledger.mark_triggered(record)
    ledger.mark_trade_ready(record)
    ledger.mark_traded(record)
    ledger.record_outcome(record, Outcome("TEST", now, 20, 22, 19, 22, 2.0, -0.25, 2.0, "WIN"))

    record_id = store.create(record)
    store.update(record_id, record)
    restored = store.get(record_id)

    assert restored is not None
    assert restored.symbol == "TEST"
    assert restored.trigger_confirmed is True
    assert restored.trade_ready is True
    assert restored.traded is True
    assert restored.outcome is not None
    assert restored.outcome.outcome_r == 2.0
    assert restored.outcome.result == "WIN"


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_candidate_returns_404():
    client = TestClient(app)
    response = client.get("/api/v1/candidates/DOESNOTEXIST")
    assert response.status_code == 404


def test_scan_processing_persists_trade_ready_candidate():
    client = TestClient(app)
    payload = {
        "symbol": "APITEST",
        "discovered_at": "2026-09-06T13:00:00+00:00",
        "catalyst_score": 90,
        "technical_score": 95,
        "relative_strength_score": 90,
        "liquidity_score": 95,
        "last_price": 20.0,
        "entry_trigger": 20.0,
        "stop_price": 19.0,
        "target_price": 22.0,
        "data_verified": True,
        "adv_shares": 1_000_000,
        "adv_dollars": 20_000_000,
        "trigger_confirmed": True,
        "equity": 2905.0,
    }
    response = client.post("/api/v1/scans/process", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["candidate"]["state"] == "TRADE_READY"
    assert body["risk_decision"]["approved"] is True
    assert body["risk_decision"]["shares"] == 29
    assert body["risk_decision"]["reward_risk"] == 2.0
    assert body["execution_reasons"] == []

    persisted = client.get("/api/v1/candidates/APITEST")
    assert persisted.status_code == 200
    assert persisted.json()["state"] == "TRADE_READY"


def test_scan_processing_rejects_unverified_data():
    client = TestClient(app)
    payload = {
        "symbol": "DATAFAIL",
        "discovered_at": "2026-09-06T13:00:00+00:00",
        "catalyst_score": 90,
        "technical_score": 95,
        "relative_strength_score": 90,
        "liquidity_score": 95,
        "last_price": 20.0,
        "entry_trigger": 20.0,
        "stop_price": 19.0,
        "target_price": 22.0,
        "data_verified": False,
        "adv_shares": 1_000_000,
        "adv_dollars": 20_000_000,
        "trigger_confirmed": True,
        "equity": 2905.0,
    }
    response = client.post("/api/v1/scans/process", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["candidate"]["state"] == "INVALIDATED"
    assert "DATA_NOT_VERIFIED" in body["execution_reasons"]
    assert body["risk_decision"] is None


def test_system_status_exposes_candidate_counts():
    client = TestClient(app)
    response = client.get("/api/v1/system")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "tradegpt-v2"
    assert body["live_execution_enabled"] is False
    assert body["options_enabled"] is False
    assert body["zero_dte_enabled"] is False
    assert body["broker_orders_enabled"] is False
    assert body["candidate_count"] >= 2
    assert "TRADE_READY" in body["state_counts"]
