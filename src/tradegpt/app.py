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


def _learning_summary(records: list[LearningRecord]) -> dict[str, float | int]:
    resolved = [record.outcome for record in records if record.outcome is not None and record.outcome.outcome_r is not None]
    wins = [outcome for outcome in resolved if outcome.outcome_r is not None and outcome.outcome_r > 0]
    losses = [outcome for outcome in resolved if outcome.outcome_r is not None and outcome.outcome_r < 0]
    total_r = sum(outcome.outcome_r for outcome in resolved if outcome.outcome_r is not None)
    return {
        "discoveries": len(records),
        "trade_ready": sum(record.trade_ready for record in records),
        "traded": sum(record.traded for record in records),
        "missed_opportunities": sum(record.missed_opportunity for record in records),
        "resolved_outcomes": len(resolved),
        "win_rate_pct": (len(wins) / len(resolved) * 100) if resolved else 0.0,
        "average_r": (total_r / len(resolved)) if resolved else 0.0,
        "total_r": total_r,
        "average_win_r": (sum(outcome.outcome_r for outcome in wins if outcome.outcome_r is not None) / len(wins)) if wins else 0.0,
        "average_loss_r": (sum(outcome.outcome_r for outcome in losses if outcome.outcome_r is not None) / len(losses)) if losses else 0.0,
    }


def _scan_run_payload(run: ScanRun) -> dict[str, object]:
    return {
        "scan_id": run.scan_id,
        "scheduled_at": run.scheduled_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "status": run.status,
        "error": run.error,
    }


def _learning_payload(record_id: int, record: LearningRecord) -> dict[str, object]:
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
        "reasons": record.reasons,
        "outcome": None if record.outcome is None else {
            "symbol": record.outcome.symbol,
            "evaluated_at": record.outcome.evaluated_at,
            "entry_price": record.outcome.entry_price,
            "exit_price": record.outcome.exit_price,
            "stop_price": record.outcome.stop_price,
            "target_price": record.outcome.target_price,
            "outcome_r": record.outcome.outcome_r,
            "max_adverse_excursion_r": record.outcome.max_adverse_excursion_r,
            "max_favorable_excursion_r": record.outcome.max_favorable_excursion_r,
            "result": record.outcome.result,
        },
    }


@app.get("/health")
def health() -> dict[str, object]:
    return health_payload()


@app.get("/api/v1/candidates")
def list_candidates() -> list[dict]:
    return [candidate_payload(candidate) for candidate in store.list()]


@app.get("/api/v1/candidates/{symbol}")
def get_candidate(symbol: str) -> dict:
    candidate = store.get(symbol.upper())
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return candidate_payload(candidate)


@app.delete("/api/v1/candidates/{symbol}", status_code=204)
def delete_candidate(symbol: str) -> None:
    if store.get(symbol.upper()) is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    store.delete(symbol.upper())


@app.post("/api/v1/scans/process")
def process_scan(request: ScanRequest) -> dict:
    scan_input = ScanInput(
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
    ledger = AuditLedger()
    result = ScanOrchestrator().process(
        scan_input,
        equity=request.equity,
        current_heat=request.current_heat,
        daily_loss=request.daily_loss,
        exceptional=request.exceptional,
        ledger=ledger,
    )
    persisted = store.upsert(result.candidate)
    for event in ledger.all():
        audit_store.append(event)
    return {"candidate": candidate_payload(persisted), "risk": result.risk_decision, "execution_reasons": result.execution_reasons}


@app.get("/api/v1/scheduler")
def scheduler_status(now: datetime | None = Query(default=None)) -> dict[str, object]:
    status = scheduler_service.status(now)
    return {
        "timezone": status.timezone,
        "next_scan_id": status.next_scan_id,
        "next_run_at": status.next_run_at,
        "scans": list(status.scans),
    }


@app.get("/api/v1/scheduler/due")
def scheduler_due(now: datetime | None = Query(default=None)) -> dict[str, object]:
    moment = now if isinstance(now, datetime) else datetime.now(timezone.utc)
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
def forward_test(record_id: int, request: ForwardTestRequest) -> dict:
    record = learning_store.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="learning record not found")
    try:
        result = evaluate_learning_record(record, request.entry_price, request.stop_price, request.target_price, request.prices, request.evaluated_at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _save_learning(record_id, record, "LEARNING_FORWARD_TEST", {"result": result.result, "outcome_r": result.outcome_r})


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
    learning = _learning_summary(learning_store.list())
    return {
        "service": "tradegpt-v2",
        "version": "2.0.0-alpha.7",
        "candidates": len(candidates),
        "candidate_count": len(candidates),
        "state_counts": state_counts,
        "learning": learning,
        "live_execution_enabled": False,
        "options_enabled": False,
        "zero_dte_enabled": False,
        "broker_orders_enabled": False,
        "execution": {"broker_connected": False, "orders_enabled": False},
    }
