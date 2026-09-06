from __future__ import annotations

from datetime import datetime, timezone

from .learning import LearningLedger
from .persistence import PersistentCandidateStore


def system_snapshot(*, store: PersistentCandidateStore, learning: LearningLedger) -> dict[str, object]:
    candidates = store.list()
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.state.value] = counts.get(candidate.state.value, 0) + 1
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(candidates),
        "state_counts": counts,
        "learning": learning.summary(),
        "execution": {
            "live_enabled": False,
            "broker_orders_enabled": False,
            "options_enabled": False,
            "zero_dte_enabled": False,
        },
    }
