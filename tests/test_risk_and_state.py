from src.risk_engine import RiskInput, evaluate
from src.state_machine import State, transition


def valid_input(**overrides):
    values = dict(
        equity=2000.0,
        entry=10.0,
        stop=9.0,
        target=12.0,
        adv_shares=1_000_000,
        adv_dollars=10_000_000.0,
        data_verified=True,
    )
    values.update(overrides)
    return RiskInput(**values)


def test_valid_trade_passes():
    approved, reasons = evaluate(valid_input())
    assert approved is True
    assert reasons == []


def test_unverified_data_fails_closed():
    approved, reasons = evaluate(valid_input(data_verified=False))
    assert approved is False
    assert "DATA NOT VERIFIED" in reasons


def test_reward_risk_gate():
    approved, reasons = evaluate(valid_input(target=11.5))
    assert approved is False
    assert "reward/risk below minimum" in reasons


def test_state_machine_rejects_illegal_transition():
    try:
        transition(State.DISCOVERED, State.MANAGE)
    except ValueError:
        return
    raise AssertionError("illegal transition was accepted")
