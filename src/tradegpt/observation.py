from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import Candidate


@dataclass(frozen=True)
class ScanObservation:
    """Immutable observation of a candidate at one scheduled scan."""

    scan_id: str
    scheduled_at: datetime
    evaluated_at: datetime
    candidate: Candidate
    discovery_source: str
    discovery_evidence: tuple[str, ...]
