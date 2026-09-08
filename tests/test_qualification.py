from datetime import datetime, timezone

from tradegpt.market_data import QuoteSnapshot
from tradegpt.models import CandidateState
from tradegpt.providers.configured import ConfiguredMarketDataProvider
from tradegpt.qualification import QualificationRequest, QualificationService, StaticProvider

NOW = datetime(2026, 9, 6, 13, 0, tzinfo=timezone.utc)


def request(**overrides):
    values = dict(
        symbol="TEST",
        catalyst_score=100,
        technical_score=100,
        relative_strength_score=100,
        liquidity_score=100,
        entry_trigger=20.0,
        stop_price=19.0,
        target_price=22.0,
        trigger_confirmed=True,
    )
    values.update(overrides)
    return QualificationRequest(**values)


def verified_snapshot(symbol="TEST", **overrides):
    values = dict(
        symbol=symbol,
        timestamp=NOW,
        last_price=20.0,
        vwap=19.8,
        rvol=2.5,
        relative_strength=91.0,
        adv_shares=1_000_000,
        adv_dollars=20_000_000,
        verified=True,
    )
    values.update(overrides)
    return QuoteSnapshot(**values)


def test_provider_to_validation_to_trade_ready_is_end_to_end():
    service = QualificationService(StaticProvider(verified_snapshot("snap")))
    result = service.qualify(request(symbol="snap"), equity=2905, now=NOW)
    assert result.candidate.state is CandidateState.TRADE_READY
    assert result.risk_decision is not None
    assert result.risk_decision.shares == 29


def test_provider_snapshot_symbol_mismatch_fails_closed():
    service = QualificationService(StaticProvider(verified_snapshot("OTHER")))
    result = service.qualify(request(symbol="TEST"), equity=2905, now=NOW)
    assert result.candidate.state is CandidateState.INVALIDATED
    assert result.candidate.symbol == "TEST"
    assert result.candidate.data_verified is False
    assert "DATA_NOT_VERIFIED" in result.execution_reasons


def test_stale_provider_data_cannot_reach_trade_ready_even_with_perfect_scores():
    stale = verified_snapshot(timestamp=datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc))
    service = QualificationService(StaticProvider(stale))
    result = service.qualify(request(), equity=2905, now=NOW)
    assert result.candidate.state is CandidateState.INVALIDATED
    assert result.candidate.data_verified is False
    assert "DATA_NOT_VERIFIED" in result.execution_reasons


def test_incomplete_provider_data_cannot_reach_trade_ready():
    incomplete = verified_snapshot(rvol=None)
    service = QualificationService(StaticProvider(incomplete))
    result = service.qualify(request(), equity=2905, now=NOW)
    assert result.candidate.state is CandidateState.INVALIDATED
    assert result.candidate.data_verified is False
    assert "DATA_NOT_VERIFIED" in result.execution_reasons


def test_provider_exception_fails_closed():
    def failing(_symbol):
        raise RuntimeError("network down")

    provider = ConfiguredMarketDataProvider(fetcher=failing, provider_name="test")
    service = QualificationService(provider)
    result = service.qualify(request(), equity=2905, now=NOW)
    assert result.candidate.state is CandidateState.INVALIDATED
    assert result.candidate.data_verified is False
    assert "DATA_NOT_VERIFIED" in result.execution_reasons


def test_unconfigured_provider_fails_closed():
    provider = ConfiguredMarketDataProvider(provider_name="none")
    service = QualificationService(provider)
    result = service.qualify(request(), equity=2905, now=NOW)
    assert result.candidate.state is CandidateState.INVALIDATED
    assert result.candidate.data_verified is False
    assert "DATA_NOT_VERIFIED" in result.execution_reasons
