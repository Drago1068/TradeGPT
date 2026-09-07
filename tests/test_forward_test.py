import pytest

from tradegpt.forward_test import evaluate_path


def test_target_outcome_and_excursions():
    result = evaluate_path(
        entry_price=20.0,
        stop_price=19.0,
        target_price=22.0,
        prices=[20.5, 21.25, 22.0],
    )
    assert result.outcome_r == 2.0
    assert result.max_adverse_excursion_r == 0.5
    assert result.max_favorable_excursion_r == 2.0
    assert result.result == "TARGET"


def test_stop_outcome():
    result = evaluate_path(
        entry_price=20.0,
        stop_price=19.0,
        target_price=22.0,
        prices=[19.75, 19.0, 21.0],
    )
    assert result.outcome_r == -1.0
    assert result.max_adverse_excursion_r == -1.0
    assert result.max_favorable_excursion_r == 1.0
    assert result.result == "STOPPED"


def test_open_path_marks_unresolved():
    result = evaluate_path(
        entry_price=20.0,
        stop_price=19.0,
        target_price=22.0,
        prices=[20.5, 21.0],
    )
    assert result.outcome_r == 1.0
    assert result.result == "OPEN"


def test_invalid_geometry_is_rejected():
    with pytest.raises(ValueError, match="stop_price"):
        evaluate_path(
            entry_price=20.0,
            stop_price=20.0,
            target_price=22.0,
            prices=[21.0],
        )
