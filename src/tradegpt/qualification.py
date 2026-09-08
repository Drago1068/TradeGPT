from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .market_data import MarketDataProvider, QuoteSnapshot, unverified_snapshot, validate_snapshot
from .orchestration import OrchestrationResult, ScanInput, ScanOrchestrator


@dataclass(frozen=True)
class QualificationRequest:
    symbol: str
    catalyst_score: float
    technical_score: float
    relative_strength_score: float
    liquidity_score: float
    entry_trigger: float | None
    stop_price: float | None
    target_price: float | None
    trigger_confirmed: bool = False
    discovery_source: str = "UNKNOWN"
    discovery_evidence: tuple[str, ...] = ()


class QualificationService:
    """Provider -> validation -> orchestration boundary.

    Strategy code receives only validated snapshot-derived inputs. Provider failures,
    stale data, incomplete snapshots, and symbol-identity mismatches remain fail-closed
    as DATA_NOT_VERIFIED.
    """

    def __init__(self, provider: MarketDataProvider, *, orchestrator: ScanOrchestrator | None = None) -> None:
        self.provider = provider
        self.orchestrator = orchestrator or ScanOrchestrator()

    def qualify(
        self,
        request: QualificationRequest,
        *,
        equity: float,
        now: datetime,
        current_heat: float = 0.0,
        daily_loss: float = 0.0,
        exceptional: bool = False,
        max_age_seconds: float = 30.0,
    ) -> OrchestrationResult:
        requested_symbol = request.symbol.strip().upper()
        raw = self.provider.snapshot(requested_symbol)
        returned_symbol = raw.symbol.strip().upper()

        # Never allow a provider response for one security to be attributed to
        # another requested security. Treat the response as unverified and keep
        # the requested symbol on the candidate for auditability.
        if returned_symbol != requested_symbol:
            snapshot = unverified_snapshot(
                requested_symbol,
                now,
                "SYMBOL_MISMATCH",
                source=raw.source,
            )
        else:
            snapshot = validate_snapshot(raw, now=now, max_age_seconds=max_age_seconds)

        scan = ScanInput.from_snapshot(
            snapshot,
            catalyst_score=request.catalyst_score,
            technical_score=request.technical_score,
            relative_strength_score=request.relative_strength_score,
            liquidity_score=request.liquidity_score,
            entry_trigger=request.entry_trigger,
            stop_price=request.stop_price,
            target_price=request.target_price,
            trigger_confirmed=request.trigger_confirmed,
        )
        return self.orchestrator.process(
            scan,
            equity=equity,
            current_heat=current_heat,
            daily_loss=daily_loss,
            exceptional=exceptional,
        )


class StaticProvider:
    """Small deterministic provider useful for acceptance tests and local development."""

    def __init__(self, snapshot: QuoteSnapshot) -> None:
        self._snapshot = snapshot

    def snapshot(self, symbol: str) -> QuoteSnapshot:
        return self._snapshot
