from datetime import datetime, timezone

from fastapi.testclient import TestClient

from tradegpt.app import app
from tradegpt.db import init_db, make_engine, make_session_factory
from tradegpt.models import Candidate, CandidateState
from tradegpt.persistence import PersistentCandidateStore


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


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_candidate_returns_404():
    client = TestClient(app)
    response = client.get("/api/v1/candidates/DOESNOTEXIST")
    assert response.status_code == 404
