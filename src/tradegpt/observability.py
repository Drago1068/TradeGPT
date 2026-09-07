from __future__ import annotations

from datetime import datetime, timezone

from .learning import LearningRecord
from .persistence import PersistentCandidateStore, PersistentLearningStore


def _learning_summary(records: list[LearningRecord]) -> dict[str, float | int]:
    rs = [
        float(record.outcome.outcome_r)
        for record in records
        if record.outcome is not None and record.outcome.outcome_r is not None
    ]
    wins = [value for value in rs if value > 0]
    losses = [value for value in rs if value < 0]
    return {
        "discoveries": len(records),
        "trade_ready": sum(record.trade_ready for record in records),
        "traded": sum(record.traded for record in records),
        "missed_opportunities": sum(record.missed_opportunity for record in records),
        "resolved_outcomes": len(rs),
        "win_rate_pct": round(len(wins) / len(rs) * 100, 2) if rs else 0.0,
        "average_r": round(sum(rs) / len(rs), 3) if rs else 0.0,
        "total_r": round(sum(rs), 3),
        "average_win_r": round(sum(wins) / len(wins), 3) if wins else 0.0,
        "average_loss_r": round(sum(losses) / len(losses), 3) if losses else 0.0,
    }


def system_snapshot(
    *,
    store: PersistentCandidateStore,
    learning: PersistentLearningStore,
) -> dict[str, object]:
    candidates = store.list()
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.state.value] = counts.get(candidate.state.value, 0) + 1
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(candidates),
        "state_counts": counts,
        "learning": _learning_summary(learning.list()),
        "execution": {
            "live_enabled": False,
            "broker_orders_enabled": False,
            "options_enabled": False,
            "zero_dte_enabled": False,
        },
    }
