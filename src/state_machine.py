"""Trade lifecycle state machine with explicit legal transitions."""

from enum import Enum


class State(str, Enum):
    DISCOVERED = "DISCOVERED"
    WATCH = "WATCH"
    ARMED = "ARMED"
    TRIGGERED = "TRIGGERED"
    TRADE_READY = "TRADE_READY"
    ENTER = "ENTER"
    MANAGE = "MANAGE"
    EXIT = "EXIT"
    INVALIDATED = "INVALIDATED"
    REJECTED = "REJECTED"


TRANSITIONS: dict[State, set[State]] = {
    State.DISCOVERED: {State.WATCH, State.REJECTED, State.INVALIDATED},
    State.WATCH: {State.ARMED, State.REJECTED, State.INVALIDATED},
    State.ARMED: {State.TRIGGERED, State.REJECTED, State.INVALIDATED},
    State.TRIGGERED: {State.TRADE_READY, State.REJECTED, State.INVALIDATED},
    State.TRADE_READY: {State.ENTER, State.REJECTED, State.INVALIDATED},
    State.ENTER: {State.MANAGE, State.EXIT},
    State.MANAGE: {State.EXIT, State.INVALIDATED},
    State.EXIT: set(),
    State.INVALIDATED: set(),
    State.REJECTED: set(),
}


def transition(current: State, requested: State) -> State:
    if requested not in TRANSITIONS[current]:
        raise ValueError(f"Illegal transition: {current.value} -> {requested.value}")
    return requested
