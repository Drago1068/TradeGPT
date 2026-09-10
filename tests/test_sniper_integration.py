from tradegpt.sniper import SniperEvidence, SniperPolicy, rank_sniper_candidates


def test_sniper_policy_produces_zero_to_three_without_padding():
    policy = SniperPolicy(a_plus_min=85)
    base = dict(
        catalyst_quality=90, catalyst_verified=True, catalyst_explains_move=True,
        abnormal_volume=85, dollar_volume=85, relative_strength=85,
        sector_relative_strength=80, price_structure=85, trade_location=85,
        liquidity=85, regime_fit=80, reward_risk=2.5, pre_breakout=80,
        gap_quality=80, volume_quality=80, data_verified=True,
    )
    items = [SniperEvidence(symbol=s, **base) for s in ("AAA", "BBB", "CCC", "DDD")]
    ranked = rank_sniper_candidates(items, policy=policy, limit=3)
    assert len(ranked) == 3
    assert [x[0].symbol for x in ranked] == ["AAA", "BBB", "CCC"]
