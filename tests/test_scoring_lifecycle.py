from datetime import datetime, timezone

import pytest

from tradegpt.ledger import AuditLedger
from tradegpt.lifecycle import CandidateLifecycle
from tradegpt.models import Candidate, CandidateState
from tradegpt.scoring import composite_score, execution_gate, score_band


def candidate(**overrides):
    values = dict(
        symbol="TEST",
        discovered_at=datetime.now(timezone.utc),
        state=CandidateState.DISCOVERED,
        score=95.0,
        catalyst_score=95.0,
        technical_score=95.0,
        relative_strength_score=95.0,
        liquidity_score=95.0,
        entry_trigger=20.0,
        stop_price=19.0,
        target_price=22.0,
        last_price=19.8,
        data_verified=True,
    )
    values.update(overrides)
    return Candidate(**values)


def test_weighted_score_and_bands():
    assert composite_score(catalyst=100, technical=100, relative_strength=100, liquidity=100) == 100
    assert score_band(90) == "A+"
    assert score_band(82) == "A"
    assert score_band(74) == "WATCH"
    assert score_band(65) == "DISCOVERY"
    assert score_band(64.99) == "PASS"


def test_execution_gate_requires_all_hard_conditions():
    approved, reasons = execution_gate(candidate())
    assert approved
    assert reasons == ()

    approved, reasons = execution_gate(candidate(data_verified=False))
    assert not approved
    assert "DATA_NOT_VERIFIED" in reasons

    approved, reasons = execution_gate(candidate(last_price=20.50))
    assert not approved
    assert "CHASE_GUARD" in reasons


def test_lifecycle_records_transitions():
    ledger = AuditLedger()
    lifecycle = CandidateLifecycle(ledger)
    moved = lifecycle.move(candidate(), CandidateState.WATCH, reason="initial qualification")
    assert moved.state is CandidateState.WATCH
    assert len(ledger.all()) == 1
    assert ledger.all()[0].event_type == "STATE_TRANSITION"
    assert ledger.all()[0].payload["from_state"] == "DISCOVERED"


def test_invalid_transition_is_rejected_and_not_logged():
    ledger = AuditLedger()
    lifecycle = CandidateLifecycle(ledger)
    with pytest.raises(ValueError):
        lifecycle.move(candidate(), CandidateState.ENTERED)
    assert ledger.all() == ()
