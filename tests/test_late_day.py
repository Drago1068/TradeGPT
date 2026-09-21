from tradegpt.late_day import LateDayEvidence, late_day_gate, late_day_score

def test_late_day_score_uses_all_required_dimensions():
    evidence=LateDayEvidence(80,90,85,95,90,80,True,True)
    assert late_day_score(evidence)>80

def test_late_day_requires_invalidation_and_chase_threshold():
    evidence=LateDayEvidence(80,80,80,80,80,80,False,True)
    ok,reasons=late_day_gate(evidence)
    assert not ok and "NO_INVALIDATION" in reasons
    evidence=LateDayEvidence(80,80,80,80,80,80,True,False)
    ok,reasons=late_day_gate(evidence)
    assert not ok and "NO_CHASE_THRESHOLD" in reasons
