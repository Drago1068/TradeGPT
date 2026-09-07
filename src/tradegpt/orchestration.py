from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .ledger import AuditLedger
from .lifecycle import CandidateLifecycle
from .market_data import QuoteSnapshot
from .models import Candidate, CandidateState
from .risk import RiskDecision, RiskPolicy, evaluate_trade
from .scoring import ScorePolicy, composite_score, execution_gate


@dataclass(frozen=True)
class ScanInput:
    symbol: str
    discovered_at: datetime
    catalyst_score: float
    technical_score: float
    relative_strength_score: float
    liquidity_score: float
    last_price: float | None
    entry_trigger: float | None
    stop_price: float | None
    target_price: float | None
    data_verified: bool
    adv_shares: int | None
    adv_dollars: float | None
    trigger_confirmed: bool = False

    @classmethod
    def from_snapshot(
        cls,
        snapshot: QuoteSnapshot,
        *,
        catalyst_score: float,
        technical_score: float,
        relative_strength_score: float,
        liquidity_score: float,
        entry_trigger: float | None,
        stop_price: float | None,
        target_price: float | None,
        trigger_confirmed: bool = False,
    ) -> "ScanInput":
        """Build strategy input from one provider snapshot without hiding data gaps."""
        return cls(
            symbol=snapshot.symbol,
            discovered_at=snapshot.timestamp,
            catalyst_score=catalyst_score,
            technical_score=technical_score,
            relative_strength_score=relative_strength_score,
            liquidity_score=liquidity_score,
            last_price=snapshot.last_price,
            entry_trigger=entry_trigger,
            stop_price=stop_price,
            target_price=target_price,
            data_verified=snapshot.verified,
            adv_shares=int(snapshot.adv_shares) if snapshot.adv_shares is not None else None,
            adv_dollars=snapshot.adv_dollars,
            trigger_confirmed=trigger_confirmed,
        )


@dataclass(frozen=True)
class OrchestrationResult:
    candidate: Candidate
    risk_decision: RiskDecision | None
    execution_reasons: tuple[str, ...]


class ScanOrchestrator:
    """Deterministic scan pipeline: score -> state -> trigger -> hard gates -> risk."""

    def __init__(
        self,
        *,
        lifecycle: CandidateLifecycle | None = None,
        score_policy: ScorePolicy | None = None,
        risk_policy: RiskPolicy | None = None,
    ) -> None:
        self.lifecycle = lifecycle or CandidateLifecycle()
        self.score_policy = score_policy or ScorePolicy()
        self.risk_policy = risk_policy or RiskPolicy()

    def process(
        self,
        scan: ScanInput,
        *,
        equity: float,
        current_heat: float = 0.0,
        daily_loss: float = 0.0,
        exceptional: bool = False,
    ) -> OrchestrationResult:
        score = composite_score(
            catalyst=scan.catalyst_score,
            technical=scan.technical_score,
            relative_strength=scan.relative_strength_score,
            liquidity=scan.liquidity_score,
        )
        candidate = Candidate(
            symbol=scan.symbol.upper(),
            discovered_at=scan.discovered_at,
            score=score,
            catalyst_score=scan.catalyst_score,
            technical_score=scan.technical_score,
            relative_strength_score=scan.relative_strength_score,
            liquidity_score=scan.liquidity_score,
            entry_trigger=scan.entry_trigger,
            stop_price=scan.stop_price,
            target_price=scan.target_price,
            last_price=scan.last_price,
            data_verified=scan.data_verified,
        )

        if score < self.score_policy.discovery_min:
            self.lifecycle.move(candidate, CandidateState.REJECTED, reason="SCORE_BELOW_DISCOVERY")
            candidate.rejection_reasons.append("SCORE_BELOW_DISCOVERY")
            return OrchestrationResult(candidate, None, ("SCORE_BELOW_DISCOVERY",))

        if score >= self.score_policy.watch_min:
            self.lifecycle.move(candidate, CandidateState.WATCH, reason="SCORE_MEETS_WATCH")
        if score >= self.score_policy.armed_min:
            self.lifecycle.move(candidate, CandidateState.ARMED, reason="SCORE_MEETS_ARMED")

        # A+ is intentionally NOT a state transition. It is only an execution gate.
        if not scan.trigger_confirmed:
            return OrchestrationResult(candidate, None, ())

        if candidate.state != CandidateState.ARMED:
            reason = "TRIGGER_REQUIRES_ARMED"
            candidate.rejection_reasons.append(reason)
            return OrchestrationResult(candidate, None, (reason,))

        self.lifecycle.move(candidate, CandidateState.TRIGGERED, reason="TRIGGER_CONFIRMED")
        executable, reasons = execution_gate(candidate, policy=self.score_policy)
        if not executable:
            candidate.rejection_reasons.extend(reasons)
            self.lifecycle.move(candidate, CandidateState.INVALIDATED, reason="EXECUTION_GATE_FAILED")
            return OrchestrationResult(candidate, None, reasons)

        risk = evaluate_trade(
            equity=equity,
            entry=candidate.entry_trigger,
            stop=candidate.stop_price,
            target=candidate.target_price,
            current_heat=current_heat,
            daily_loss=daily_loss,
            adv_shares=scan.adv_shares,
            adv_dollars=scan.adv_dollars,
            data_verified=scan.data_verified,
            exceptional=exceptional,
            policy=self.risk_policy,
        )
        if not risk.approved:
            candidate.rejection_reasons.extend(risk.reasons)
            self.lifecycle.move(candidate, CandidateState.INVALIDATED, reason="RISK_GATE_FAILED")
            return OrchestrationResult(candidate, risk, risk.reasons)

        self.lifecycle.move(candidate, CandidateState.TRADE_READY, reason="EXECUTION_AND_RISK_GATES_PASSED")
        self.lifecycle.ledger.record(
            "TRADE_READY",
            candidate.symbol,
            state=candidate.state.value,
            shares=risk.shares,
            risk_dollars=risk.risk_dollars,
            reward_risk=risk.reward_risk,
        )
        return OrchestrationResult(candidate, risk, ())
