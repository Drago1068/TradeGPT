from datetime import datetime, timezone

from tradegpt.db import init_db, make_engine, make_session_factory
from tradegpt.ledger import AuditEvent
from tradegpt.persistence import PersistentAuditStore


def test_persistent_audit_round_trip(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'audit.db'}")
    init_db(engine)
    store = PersistentAuditStore(make_session_factory(engine))
    event = AuditEvent(
        event_type="TRADE_READY",
        symbol="TEST",
        timestamp=datetime.now(timezone.utc),
        state="TRADE_READY",
        payload={"shares": 29, "risk_dollars": 29.0},
    )

    store.append(event)
    restored = store.for_symbol("test")

    assert len(restored) == 1
    assert restored[0].event_type == "TRADE_READY"
    assert restored[0].symbol == "TEST"
    assert restored[0].state == "TRADE_READY"
    assert restored[0].payload == {"shares": 29, "risk_dollars": 29.0}
