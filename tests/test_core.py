from datetime import datetime, timezone

import pytest

from tradegpt.models import CandidateState
from tradegpt.risk import evaluate_trade
from tradegpt.state_machine import transition


def test_valid_state_progression():
    state = CandidateState.DISCOVERED
    for target in (
        CandidateState.WATCH,
        CandidateState.ARMED,
        CandidateState.TRIGGERED,
        CandidateState.TRADE_READY,
    ):
        state = transition(state, target)
    assert state is CandidateState.TRADE_READY


def test_invalid_transition_is_rejected():
    with pytest.raises(ValueError):
        transition(CandidateState.DISCOVERED, CandidateState.ENTERED)


def test_risk_gate_rejects_unverified_data():
    result = evaluate_trade(
        equity=2905,
        entry=20,
        stop=19,
        target=22,
        adv_shares=1_000_000,
        adv_dollars=20_000_000,
        data_verified=False,
    )
    assert not result.approved
    assert "DATA_NOT_VERIFIED" in result.reasons


def test_valid_stock_trade_sizes_from_risk_budget():
    result = evaluate_trade(
        equity=2905,
        entry=20,
        stop=19,
        target=22,
        adv_shares=1_000_000,
        adv_dollars=20_000_000,
        data_verified=True,
    )
    assert result.approved
    assert result.shares == 29
    assert result.risk_dollars <= 29.05
    assert result.reward_risk == pytest.approx(2.0)
