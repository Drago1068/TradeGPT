from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query

from .api import candidate_payload, health_payload
from .db import init_db, make_engine
from .models import Candidate, CandidateState
from .persistence import PersistentCandidateStore

app = FastAPI(title="TradeGPT V2", version="2.0.0-alpha.1")
engine = make_engine()
init_db(engine)
store = PersistentCandidateStore()


@app.get("/health")
def health() -> dict[str, str]:
    return health_payload()


@app.get("/api/v1/candidates")
def list_candidates(
    state: CandidateState | None = Query(default=None),
) -> list[dict]:
    return [candidate_payload(candidate) for candidate in store.list(state)]


@app.get("/api/v1/candidates/{symbol}")
def get_candidate(symbol: str) -> dict:
    candidate = store.get(symbol.upper())
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return candidate_payload(candidate)


@app.post("/api/v1/candidates", status_code=201)
def upsert_candidate(candidate: Candidate) -> dict:
    return candidate_payload(store.upsert(candidate))


@app.get("/api/v1/system")
def system_status() -> dict[str, object]:
    return {
        "service": "tradegpt-v2",
        "mode": "research",
        "live_execution_enabled": False,
        "options_enabled": False,
        "zero_dte_enabled": False,
        "broker_orders_enabled": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
