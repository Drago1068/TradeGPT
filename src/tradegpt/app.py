from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from .api import candidate_payload, health_payload
from .audit_persistence import PersistentAuditStore
from .db import init_db, make_engine
from .ledger import AuditLedger
from .lifecycle import CandidateLifecycle
from .models import Candidate, CandidateState
from .orchestration import ScanInput, ScanOrchestrator
from .persistence import PersistentCandidateStore

app = FastAPI(title="TradeGPT V2", version="2.0.0-alpha.2")
engine = make_engine()
init_db(engine)
store = PersistentCandidateStore()
audit_store = PersistentAuditStore()


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    discovered_at: datetime
    catalyst_score: float
    technical_score: float
    relative_strength_score: float
    liquidity_score: float
    last_price: float | None = None
    entry_trigger: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    data_verified: bool = False
    adv_shares: int | None = None
    adv_dollars: float | None = None
    trigger_confirmed: bool = False
    equity: float
    current_heat: float = 0.0
    daily_loss: float = 0.0
    exceptional: bool = False


def _scan_input(request: ScanRequest) -> ScanInput:
    return ScanInput(
        symbol=request.symbol,
        discovered_at=request.discovered_at,
        catalyst_score=request.catalyst_score,
        technical_score=request.technical_score,
        relative_strength_score=request.relative_strength_score,
        liquidity_score=request.liquidity_score,
        last_price=request.last_price,
        entry_trigger=request.entry_trigger,
        stop_price=request.stop_price,
        target_price=request.target_price,
        data_verified=request.data_verified,
        adv_shares=request.adv_shares,
        adv_dollars=request.adv_dollars,
        trigger_confirmed=request.trigger_confirmed,
    )


def _risk_payload(risk) -> dict | None:
    if risk is None:
        return None
    return {
        "approved": risk.approved,
        "shares": risk.shares,
        "risk_dollars": risk.risk_dollars,
        "reward_risk": risk.reward_risk,
        "reasons": list(risk.reasons),
    }


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


@app.post("/api/v1/scans/process")
def process_scan(request: ScanRequest) -> dict:
    ledger = AuditLedger()
    result = ScanOrchestrator(
        lifecycle=CandidateLifecycle(ledger),
    ).process(
        _scan_input(request),
        equity=request.equity,
        current_heat=request.current_heat,
        daily_loss=request.daily_loss,
        exceptional=request.exceptional,
    )
    persisted = store.upsert(result.candidate)
    for event in ledger.all():
        audit_store.append(event)
    return {
        "candidate": candidate_payload(persisted),
        "risk_decision": _risk_payload(result.risk_decision),
        "execution_reasons": list(result.execution_reasons),
    }


@app.get("/api/v1/system")
def system_status() -> dict[str, object]:
    candidates = store.list()
    state_counts = {state.value: 0 for state in CandidateState}
    for candidate in candidates:
        state_counts[candidate.state.value] += 1
    return {
        "service": "tradegpt-v2",
        "mode": "research",
        "live_execution_enabled": False,
        "options_enabled": False,
        "zero_dte_enabled": False,
        "broker_orders_enabled": False,
        "candidate_count": len(candidates),
        "state_counts": state_counts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
