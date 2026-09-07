from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from .api import candidate_payload, health_payload
from .composition import build_runtime
from .forward_learning import evaluate_learning_record
from .ledger import AuditEvent, AuditLedger
from .learning import LearningRecord, Outcome
from .lifecycle import CandidateLifecycle
from .models import Candidate, CandidateState
from .orchestration import ScanInput, ScanOrchestrator
from .scan_audit import ScanRun

app = FastAPI(title="TradeGPT V2", version="2.0.0-alpha.7")
runtime = build_runtime()
store = runtime.candidate_store
audit_store = runtime.audit_store
learning_store = runtime.learning_store
scheduler_service = runtime.scheduler


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


class LearningDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    discovered_at: datetime
    score: float
    state: CandidateState


class LearningOutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluated_at: datetime
    entry_price: float | None = None
    exit_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    outcome_r: float | None = None
    max_adverse_excursion_r: float | None = None
    max_favorable_excursion_r: float | None = None
    result: str = "UNRESOLVED"


class ForwardTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry_price: float
    stop_price: float
    target_price: float
    prices: list[float]
    evaluated_at: datetime | None = None


class ScanStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime
    started_at: datetime | None = None


class ScanCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime
    started_at: datetime
    completed_at: datetime | None = None


class ScanFailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime
    started_at: datetime
    error: str
    failed_at: datetime | None = None


class ScanMissedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime
    detected_at: datetime | None = None


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


def _learning_payload(record_id: int, record: LearningRecord) -> dict:
    outcome = record.outcome
    return {
        "id": record_id,
        "symbol": record.symbol,
        "discovered_at": record.discovered_at,
        "discovery_score": record.discovery_score,
        "discovery_state": record.discovery_state.value,
        "trigger_confirmed": record.trigger_confirmed,
        "trade_ready": record.trade_ready,
        "traded": record.traded,
        "missed_opportunity": record.missed_opportunity,
        "reasons": list(record.reasons),
        "outcome": None if outcome is None else {
            "symbol": outcome.symbol,
            "evaluated_at": outcome.evaluated_at,
            "entry_price": outcome.entry_price,
            "exit_price": outcome.exit_price,
            "stop_price": outcome.stop_price,
            "target_price": outcome.target_price,
            "outcome_r": outcome.outcome_r,
            "max_adverse_excursion_r": outcome.max_adverse_excursion_r,
            "max_favorable_excursion_r": outcome.max_favorable_excursion_r,
            "result": outcome.result,
        },
    }


def _learning_summary(records: list[LearningRecord]) -> dict[str, float | int]:
    rs = [float(r.outcome.outcome_r) for r in records if r.outcome is not None and r.outcome.outcome_r is not None]
    wins = [v for v in rs if v > 0]
    losses = [v for v in rs if v < 0]
    return {
        "discoveries": len(records),
        "trade_ready": sum(r.trade_ready for r in records),
        "traded": sum(r.traded for r in records),
        "missed_opportunities": sum(r.missed_opportunity for r in records),
        "resolved_outcomes": len(rs),
        "win_rate_pct": round(len(wins) / len(rs) * 100, 2) if rs else 0.0,
        "average_r": round(sum(rs) / len(rs), 3) if rs else 0.0,
        "total_r": round(sum(rs), 3),
        "average_win_r": round(sum(wins) / len(wins), 3) if wins else 0.0,
        "average_loss_r": round(sum(losses) / len(losses), 3) if losses else 0.0,
    }


def _scan_run_payload(run: ScanRun) -> dict:
    return {
        "scan_id": run.scan_id,
        "scheduled_at": run.scheduled_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "status": run.status,
        "error": run.error,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return health_payload()


@app.get("/api/v1/candidates")
def list_candidates(state: CandidateState | None = Query(default=None)) -> list[dict]:
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
    result = ScanOrchestrator(lifecycle=CandidateLifecycle(ledger)).process(
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


@app.get("/api/v1/scheduler")
def scheduler_status(now: datetime | None = Query(default=None)) -> dict:
    status = scheduler_service.status(now)
    return {
        "timezone": status.timezone,
        "next_run": None if status.next_run_at is None else {"scan_id": status.next_scan_id, "scheduled_at": status.next_run_at},
        "scans": list(status.scans),
    }


@app.get("/api/v1/scheduler/due")
def scheduler_due(now: datetime | None = Query(default=None)) -> dict:
    moment = now or datetime.now(timezone.utc)
    return {
        "evaluated_at": moment,
        "due": [
            {"id": schedule.id, "label": schedule.label, "time_et": schedule.time_et.isoformat(timespec="minutes")}
            for schedule in scheduler_service.due(moment)
        ],
    }


@app.post("/api/v1/scheduler/runs/{scan_id}/start")
def scheduler_start(scan_id: str, request: ScanStartRequest) -> dict:
    try:
        run = scheduler_service.start(scan_id, request.scheduled_at, request.started_at)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _scan_run_payload(run)


@app.post("/api/v1/scheduler/runs/{scan_id}/complete")
def scheduler_complete(scan_id: str, request: ScanCompleteRequest) -> dict:
    try:
        run = ScanRun(scan_id, request.scheduled_at, request.started_at)
        result = scheduler_service.complete(run, request.completed_at)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _scan_run_payload(result)


@app.post("/api/v1/scheduler/runs/{scan_id}/fail")
def scheduler_fail(scan_id: str, request: ScanFailRequest) -> dict:
    try:
        run = ScanRun(scan_id, request.scheduled_at, request.started_at)
        result = scheduler_service.fail(run, request.error, request.failed_at)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _scan_run_payload(result)


@app.post("/api/v1/scheduler/runs/{scan_id}/missed")
def scheduler_missed(scan_id: str, request: ScanMissedRequest) -> dict:
    try:
        scheduler_service.missed(scan_id, request.scheduled_at, request.detected_at)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"scan_id": scan_id, "scheduled_at": request.scheduled_at, "status": "MISSED"}


@app.post("/api/v1/learning/discoveries", status_code=201)
def create_learning_discovery(request: LearningDiscoveryRequest) -> dict:
    record = LearningRecord(symbol=request.symbol.upper(), discovered_at=request.discovered_at, discovery_score=request.score, discovery_state=request.state)
    record_id = learning_store.create(record)
    audit_store.append(AuditEvent(event_type="LEARNING_DISCOVERY", symbol=record.symbol, state=record.discovery_state.value, payload={"learning_record_id": record_id, "score": record.discovery_score}))
    return _learning_payload(record_id, record)


@app.get("/api/v1/learning")
def list_learning(symbol: str | None = Query(default=None)) -> list[dict]:
    return [_learning_payload(record_id, record) for record_id, record in learning_store.list_with_ids(symbol=symbol)]


@app.get("/api/v1/learning/summary")
def learning_summary() -> dict[str, float | int]:
    return _learning_summary(learning_store.list())


@app.get("/api/v1/learning/{record_id}")
def get_learning(record_id: int) -> dict:
    record = learning_store.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="learning record not found")
    return _learning_payload(record_id, record)


def _save_learning(record_id: int, record: LearningRecord, event_type: str, payload: dict) -> dict:
    learning_store.update(record_id, record)
    audit_store.append(AuditEvent(event_type=event_type, symbol=record.symbol, payload={"learning_record_id": record_id, **payload}))
    return _learning_payload(record_id, record)


@app.post("/api/v1/learning/{record_id}/triggered")
def mark_learning_triggered(record_id: int) -> dict:
    record = learning_store.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="learning record not found")
    record.trigger_confirmed = True
    return _save_learning(record_id, record, "LEARNING_TRIGGER_CONFIRMED", {})


@app.post("/api/v1/learning/{record_id}/trade-ready")
def mark_learning_trade_ready(record_id: int) -> dict:
    record = learning_store.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="learning record not found")
    record.trade_ready = True
    return _save_learning(record_id, record, "LEARNING_TRADE_READY", {})


@app.post("/api/v1/learning/{record_id}/traded")
def mark_learning_traded(record_id: int) -> dict:
    record = learning_store.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="learning record not found")
    record.traded = True
    return _save_learning(record_id, record, "LEARNING_TRADED", {})


@app.post("/api/v1/learning/{record_id}/missed")
def mark_learning_missed(record_id: int, reason: str = Query(min_length=1)) -> dict:
    record = learning_store.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="learning record not found")
    record.missed_opportunity = True
    record.reasons.append(reason)
    return _save_learning(record_id, record, "LEARNING_MISSED", {"reason": reason})


@app.post("/api/v1/learning/{record_id}/forward-test")
def forward_test_learning(record_id: int, request: ForwardTestRequest) -> dict:
    try:
        result = evaluate_learning_record(learning_store, record_id=record_id, entry_price=request.entry_price, stop_price=request.stop_price, target_price=request.target_price, prices=request.prices, evaluated_at=request.evaluated_at)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record = learning_store.get(record_id)
    assert record is not None
    if result is not None:
        audit_store.append(AuditEvent(event_type="LEARNING_FORWARD_TEST_RESOLVED", symbol=record.symbol, payload={"learning_record_id": record_id, "result": result.result, "outcome_r": result.outcome_r, "mae_r": result.max_adverse_excursion_r, "mfe_r": result.max_favorable_excursion_r}))
    return {"resolved": result is not None, "result": None if result is None else result.result, "outcome_r": None if result is None else result.outcome_r, "max_adverse_excursion_r": None if result is None else result.max_adverse_excursion_r, "max_favorable_excursion_r": None if result is None else result.max_favorable_excursion_r, "learning": _learning_payload(record_id, record)}


@app.post("/api/v1/learning/{record_id}/outcome")
def record_learning_outcome(record_id: int, request: LearningOutcomeRequest) -> dict:
    record = learning_store.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="learning record not found")
    if record.outcome is not None:
        raise HTTPException(status_code=409, detail="learning record already has an outcome")
    outcome_r = request.outcome_r
    if outcome_r is None and request.entry_price is not None and request.exit_price is not None and request.stop_price is not None:
        risk_per_share = abs(request.entry_price - request.stop_price)
        if risk_per_share > 0:
            outcome_r = (request.exit_price - request.entry_price) / risk_per_share
    record.outcome = Outcome(symbol=record.symbol, evaluated_at=request.evaluated_at, entry_price=request.entry_price, exit_price=request.exit_price, stop_price=request.stop_price, target_price=request.target_price, outcome_r=outcome_r, max_adverse_excursion_r=request.max_adverse_excursion_r, max_favorable_excursion_r=request.max_favorable_excursion_r, result=request.result)
    return _save_learning(record_id, record, "LEARNING_OUTCOME", {"outcome_r": outcome_r, "result": request.result})


@app.get("/api/v1/system")
def system_status() -> dict[str, object]:
    candidates = store.list()
    state_counts = {state.value: 0 for state in CandidateState}
    for candidate in candidates:
        state_counts[candidate.state.value] += 1
    return {
        "service": "tradegpt-v2",
        "version": "2.0.0-alpha.7",
        "candidates": len(candidates),
        "state_counts": state_counts,
        "learning": _learning_summary(learning_store.list()),
        "execution": {"broker_connected": False, "orders_enabled": False},
    }
