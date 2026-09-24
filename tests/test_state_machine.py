from tradegpt.models import CandidateState
from tradegpt.state_machine import can_transition, transition


def test_explicit_readiness_states_are_valid_transitions():
    assert can_transition(CandidateState.WATCH, CandidateState.NEAR_TRIGGER)
    assert can_transition(CandidateState.NEAR_TRIGGER, CandidateState.TRADE_READY_UNDERLYING)
    assert can_transition(CandidateState.TRADE_READY_UNDERLYING, CandidateState.OPTION_VALIDATION_PENDING)
    assert can_transition(CandidateState.OPTION_VALIDATION_PENDING, CandidateState.TRADE_READY)
    assert can_transition(CandidateState.TRIGGERED, CandidateState.EXECUTION_BLOCKED)
    assert transition(CandidateState.WATCH, CandidateState.NEAR_TRIGGER) is CandidateState.NEAR_TRIGGER
