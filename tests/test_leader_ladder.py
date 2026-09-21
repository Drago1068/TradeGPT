from tradegpt.leader_ladder import (
    LeaderRelationship,
    rank_with_leader_ladder,
    relationship_adjustment,
)


def test_adjustment_is_bounded_and_rewards_acceleration():
    strong = LeaderRelationship(
        group="chips",
        role="EMERGING_LEADER",
        peer_confirmation=95,
        acceleration=95,
        relative_strength=90,
        catalyst_freshness=80,
    )
    assert relationship_adjustment(strong) <= 8
    assert relationship_adjustment(strong) > 0


def test_weak_second_wave_does_not_get_free_points():
    weak = LeaderRelationship(
        group="optical",
        role="SECOND_WAVE",
        peer_confirmation=10,
        acceleration=10,
        relative_strength=20,
        catalyst_freshness=10,
    )
    assert relationship_adjustment(weak) < 0


def test_ranking_keeps_base_score_visible():
    relationships = {
        "AMD": LeaderRelationship(
            group="chips",
            role="EMERGING_LEADER",
            peer_confirmation=95,
            acceleration=95,
            relative_strength=95,
            catalyst_freshness=80,
        ),
        "CIEN": LeaderRelationship(
            group="optical",
            role="LEADER",
            peer_confirmation=55,
            acceleration=40,
            relative_strength=60,
            catalyst_freshness=95,
        ),
    }
    ranked = rank_with_leader_ladder(
        [("CIEN", 82.0), ("AMD", 80.0)],
        relationships,
    )
    assert ranked[0][0] == "AMD"
    assert ranked[0][2] > 0
