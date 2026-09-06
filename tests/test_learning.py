from datetime import datetime, timezone

from tradegpt.learning import LearningLedger, Outcome
from tradegpt.models import CandidateState


def test_learning_ledger_tracks_discovery_and_missed_opportunity():
    ledger = LearningLedger()
    record = ledger.record_discovery(
        symbol="TEST",
        discovered_at=datetime.now(timezone.utc),
        score=88.0,
        state=CandidateState.ARMED,
    )
    ledger.mark_triggered(record)
    ledger.mark_missed(record, "PRICE_MOVED_BEFORE_ENTRY")

    summary = ledger.summary()
    assert summary["discoveries"] == 1
    assert summary["missed_opportunities"] == 1
    assert summary["traded"] == 0
    assert record.trigger_confirmed is True


def test_learning_ledger_calculates_r_metrics():
    ledger = LearningLedger()
    now = datetime.now(timezone.utc)
    win = ledger.record_discovery(symbol="WIN", discovered_at=now, score=94, state=CandidateState.TRADE_READY)
    loss = ledger.record_discovery(symbol="LOSS", discovered_at=now, score=91, state=CandidateState.TRADE_READY)
    ledger.mark_trade_ready(win)
    ledger.mark_trade_ready(loss)
    ledger.mark_traded(win)
    ledger.mark_traded(loss)
    ledger.record_outcome(win, Outcome("WIN", now, 10, 12, 9, 12, 2.0, -0.25, 2.2, "WIN"))
    ledger.record_outcome(loss, Outcome("LOSS", now, 10, 9, 9, 12, -1.0, -1.0, 0.4, "LOSS"))

    summary = ledger.summary()
    assert summary["resolved_outcomes"] == 2
    assert summary["win_rate_pct"] == 50.0
    assert summary["average_r"] == 0.5
    assert summary["total_r"] == 1.0
    assert summary["average_win_r"] == 2.0
    assert summary["average_loss_r"] == -1.0
