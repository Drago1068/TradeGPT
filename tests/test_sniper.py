from tradegpt.sniper import SniperEvidence, SniperPolicy, rank_sniper_candidates, sniper_gate, sniper_score


def evidence(**overrides):
    values = dict(
        symbol="TEST",
        catalyst_quality=95,
        catalyst_verified=True,
        catalyst_explains_move=True,
        abnormal_volume=90,
        dollar_volume=90,
        relative_strength=90,
        sector_relative_strength=85,
        price_structure=90,
        trade_location=90,
        liquidity=90,
        regime_fit=80,
        reward_risk=2.5,
        pre_breakout=80,
        gap_quality=80,
        volume_quality=85,
        data_verified=True,
    )
    values.update(overrides)
    return SniperEvidence(**values)


def test_score_prefers_trade_location_and_quality():
    strong = sniper_score(evidence())
    extended = sniper_score(evidence(extended=True))
    poor_location = sniper_score(evidence(trade_location=30))
    assert strong >= 85
    assert extended < strong
    assert poor_location < strong


def test_hard_gate_requires_verified_catalyst_and_data():
    ok, reasons = sniper_gate(evidence())
    assert ok and reasons == ()
    ok, reasons = sniper_gate(evidence(data_verified=False))
    assert not ok and "DATA_NOT_VERIFIED" in reasons
    ok, reasons = sniper_gate(evidence(catalyst_verified=False))
    assert not ok and "CATALYST_NOT_VERIFIED" in reasons
    ok, reasons = sniper_gate(evidence(catalyst_explains_move=False))
    assert not ok and "MOVE_NOT_EXPLAINED_BY_CATALYST" in reasons


def test_rr_and_location_are_hard_gates():
    ok, reasons = sniper_gate(evidence(reward_risk=1.99))
    assert not ok and "REWARD_RISK_BELOW_FLOOR" in reasons
    ok, reasons = sniper_gate(evidence(trade_location=69))
    assert not ok and "TRADE_LOCATION_BELOW_FLOOR" in reasons


def test_rank_returns_fewer_than_three_when_fewer_qualify():
    candidates = [
        evidence(symbol="AAA"),
        evidence(symbol="BBB", data_verified=False),
        evidence(symbol="CCC", reward_risk=1.5),
    ]
    ranked = rank_sniper_candidates(candidates)
    assert len(ranked) == 1
    assert ranked[0][0].symbol == "AAA"


def test_custom_policy_can_raise_a_plus_floor():
    ranked = rank_sniper_candidates(
        [evidence()], policy=SniperPolicy(a_plus_min=99)
    )
    assert ranked == ()
