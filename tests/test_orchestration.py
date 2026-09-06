from datetime import datetime, timezone

from tradegpt.ledger import AuditLedger
from tradegpt.lifecycle import CandidateLifecycle
from tradegpt.models import CandidateState
from tradegpt.orchestration import ScanInput, ScanOrchestrator


NOW = datetime(2026, 9, 6, 13, 0, tzinfo=timezone.utc)


def scan(**overrides):
    values = dict(
        symbol="TEST",
        discovered_at=NOW,
        catalyst_score=90,
        technical_score=95,
        relative_strength_score=90,
        liquidity_score=95,
        last_price=20.0,
        entry_trigger=20.0,
        stop_price=19.0,
        target_price=22.0,
        data_verified=True,
        adv_shares=1_000_000,
        adv_dollars=20_000_000,
    )
    values.update(overrides)
    return ScanInput(**values)


def test_discovery_does_not_require_a_plus():
    result = ScanOrchestrator().process(
        scan(catalyst_score=70, technical_score=70, relative_strength_score=70, liquidity_score=70),
        equity=2905,
    )
    assert result.candidate.score == 70
    assert result.candidate.state is CandidateState.WATCH


def test_armed_waits_for_explicit_trigger():
    result = ScanOrchestrator().process(scan(trigger_confirmed=False), equity=2905)
    assert result.candidate.state is CandidateState.ARMED
    assert result.risk_decision is None


def test_verified_a_plus_trigger_becomes_trade_ready_with_position_size():
    ledger = AuditLedger()
    result = ScanOrchestrator(lifecycle=CandidateLifecycle(ledger)).process(
        scan(), equity=2905
    )
    assert result.candidate.state is CandidateState.TRADE_READY
    assert result.risk_decision is not None
    assert result.risk_decision.approved
    assert result.risk_decision.shares == 29
    assert result.risk_decision.risk_dollars <= 29.05
    assert result.risk_decision.reward_risk == 2.0
    assert any(e.event_type == "TRADE_READY" for e in ledger.all())


def test_data_gap_never_reaches_trade_ready():
    result = ScanOrchestrator().process(scan(data_verified=False), equity=2905)
    assert result.candidate.state is CandidateState.INVALIDATED
    assert "DATA_NOT_VERIFIED" in result.execution_reasons


def test_chase_guard_invalidates_triggered_candidate():
    result = ScanOrchestrator().process(scan(last_price=20.25), equity=2905)
    assert result.candidate.state is CandidateState.INVALIDATED
    assert "CHASE_GUARD" in result.execution_reasons


def test_risk_failure_is_preserved_as_auditable_invalidation():
    result = ScanOrchestrator().process(
        scan(adv_shares=100_000, adv_dollars=1_000_000), equity=2905
    )
    assert result.candidate.state is CandidateState.INVALIDATED
    assert result.risk_decision is not None
    assert "SHARE_LIQUIDITY_GATE" in result.risk_decision.reasons
    assert "DOLLAR_LIQUIDITY_GATE" in result.risk_decision.reasons
