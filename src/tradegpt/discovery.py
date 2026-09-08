from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from .qualification import QualificationRequest
from .scheduler import PRODUCTION_SCAN_IDS


@dataclass(frozen=True)
class DiscoveryCandidate:
    """External discovery input that is still subject to normal qualification gates."""

    request: QualificationRequest
    source: str
    evidence: tuple[str, ...] = ()


class ProductionDiscoveryPlan:
    """Deterministic, provenance-preserving plan for the three production scans.

    Discovery sources (Qwen, Perplexity, manual research, or a future native
    scanner) may populate this boundary. They do not receive execution authority.
    Every candidate is still passed through market-data validation, scoring,
    execution gates, and risk controls by QualificationService.
    """

    def __init__(self, candidates: Mapping[str, Sequence[DiscoveryCandidate]]) -> None:
        unknown = set(candidates) - set(PRODUCTION_SCAN_IDS)
        if unknown:
            raise ValueError(f"unknown production scan id(s): {sorted(unknown)}")
        self._candidates = {
            scan_id: tuple(items) for scan_id, items in candidates.items()
        }

    def requests(self, scan_id: str, scheduled_at: datetime) -> Sequence[QualificationRequest]:
        if scan_id not in PRODUCTION_SCAN_IDS:
            raise ValueError(f"unknown production scan id: {scan_id}")

        # Preserve first-seen ordering while preventing duplicate symbols from
        # one scan from consuming multiple qualification slots.
        seen: set[str] = set()
        selected: list[QualificationRequest] = []
        for item in self._candidates.get(scan_id, ()):
            symbol = item.request.symbol.strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            selected.append(item.request)
        return tuple(selected)

    def provenance(self, scan_id: str) -> tuple[DiscoveryCandidate, ...]:
        """Return the immutable source/evidence records for audit and diagnostics."""
        if scan_id not in PRODUCTION_SCAN_IDS:
            raise ValueError(f"unknown production scan id: {scan_id}")
        return self._candidates.get(scan_id, ())


class EmptyProductionDiscoveryPlan(ProductionDiscoveryPlan):
    """Explicit safe default: no discovery source is configured."""

    def __init__(self) -> None:
        super().__init__({})
