from __future__ import annotations

from .models import CandidateState


ALLOWED_TRANSITIONS: dict[CandidateState, set[CandidateState]] = {
    CandidateState.DISCOVERED: {CandidateState.WATCH, CandidateState.REJECTED, CandidateState.EXPIRED},
    CandidateState.WATCH: {CandidateState.ARMED, CandidateState.INVALIDATED, CandidateState.REJECTED, CandidateState.EXPIRED},
    CandidateState.ARMED: {CandidateState.TRIGGERED, CandidateState.INVALIDATED, CandidateState.REJECTED, CandidateState.EXPIRED},
    CandidateState.TRIGGERED: {CandidateState.TRADE_READY, CandidateState.INVALIDATED, CandidateState.REJECTED, CandidateState.EXPIRED},
    CandidateState.TRADE_READY: {CandidateState.ENTERED, CandidateState.INVALIDATED, CandidateState.REJECTED, CandidateState.EXPIRED},
    CandidateState.ENTERED: {CandidateState.MANAGE, CandidateState.EXITED},
    CandidateState.MANAGE: {CandidateState.EXITED},
    CandidateState.EXITED: set(),
    CandidateState.INVALIDATED: set(),
    CandidateState.REJECTED: set(),
    CandidateState.EXPIRED: set(),
}


def can_transition(current: CandidateState, target: CandidateState) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def transition(current: CandidateState, target: CandidateState) -> CandidateState:
    if not can_transition(current, target):
        raise ValueError(f"Invalid state transition: {current.value} -> {target.value}")
    return target
