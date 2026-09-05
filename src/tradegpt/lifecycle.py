from __future__ import annotations

from .ledger import AuditLedger
from .models import Candidate, CandidateState
from .state_machine import transition


class CandidateLifecycle:
    """Apply state-machine transitions and record every transition for auditability."""

    def __init__(self, ledger: AuditLedger | None = None) -> None:
        self.ledger = ledger or AuditLedger()

    def move(self, candidate: Candidate, new_state: CandidateState, *, reason: str | None = None) -> Candidate:
        old_state = candidate.state
        transition(old_state, new_state)
        candidate.state = new_state
        self.ledger.record(
            "STATE_TRANSITION",
            candidate.symbol,
            state=new_state.value,
            from_state=old_state.value,
            to_state=new_state.value,
            reason=reason,
        )
        return candidate
