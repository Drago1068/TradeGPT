from datetime import datetime, timezone

import pytest

from tradegpt.discovery import DiscoveryCandidate, EmptyProductionDiscoveryPlan, ProductionDiscoveryPlan
from tradegpt.qualification import QualificationRequest


NOW = datetime(2026, 9, 8, 12, 30, tzinfo=timezone.utc)


def request(symbol: str) -> QualificationRequest:
    return QualificationRequest(
        symbol=symbol,
        catalyst_score=90,
        technical_score=90,
        relative_strength_score=90,
        liquidity_score=90,
        entry_trigger=20,
        stop_price=19,
        target_price=22,
        discovery_source="QWEN",
        discovery_evidence=("fresh catalyst",),
    )


def test_production_plan_rejects_unknown_scan_ids():
    with pytest.raises(ValueError, match="unknown production scan id"):
        ProductionDiscoveryPlan({"experimental": (DiscoveryCandidate(request("ABC"), "QWEN"),)})


def test_production_plan_deduplicates_symbols_and_preserves_first_seen_order():
    plan = ProductionDiscoveryPlan(
        {
            "daily-discovery": (
                DiscoveryCandidate(request("abc"), "QWEN"),
                DiscoveryCandidate(request("ABC"), "PERPLEXITY"),
                DiscoveryCandidate(request("XYZ"), "MANUAL"),
            )
        }
    )

    requests = plan.requests("daily-discovery", NOW)

    assert [item.symbol for item in requests] == ["ABC", "XYZ"]


def test_production_plan_exposes_provenance_without_granting_execution_authority():
    candidate = DiscoveryCandidate(request("ABC"), "QWEN", ("catalyst evidence", "volume evidence"))
    plan = ProductionDiscoveryPlan({"midday-discovery": (candidate,)})

    provenance = plan.provenance("midday-discovery")

    assert provenance[0].source == "QWEN"
    assert provenance[0].evidence == ("catalyst evidence", "volume evidence")
    assert plan.requests("midday-discovery", NOW)[0].discovery_source == "QWEN"


def test_empty_plan_is_explicitly_safe():
    plan = EmptyProductionDiscoveryPlan()

    assert plan.requests("primary-qualification", NOW) == ()
    assert plan.provenance("primary-qualification") == ()


def test_unknown_scan_lookup_fails_closed():
    plan = EmptyProductionDiscoveryPlan()

    with pytest.raises(ValueError, match="unknown production scan id"):
        plan.requests("unknown", NOW)
