from sqlalchemy import inspect, text

from tradegpt.db import make_engine
from tradegpt.migrations import CURRENT_SCHEMA_VERSION, migrate


def test_migrate_creates_schema_and_version_marker():
    engine = make_engine("sqlite:///:memory:")

    assert migrate(engine) == CURRENT_SCHEMA_VERSION

    tables = set(inspect(engine).get_table_names())
    assert {"schema_version", "candidates", "audit_events", "learning_records"}.issubset(tables)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version FROM schema_version")).scalar_one() == CURRENT_SCHEMA_VERSION


def test_migrate_is_idempotent():
    engine = make_engine("sqlite:///:memory:")

    assert migrate(engine) == CURRENT_SCHEMA_VERSION
    assert migrate(engine) == CURRENT_SCHEMA_VERSION


def test_migrate_stamps_legacy_create_all_database():
    engine = make_engine("sqlite:///:memory:")
    from tradegpt.db import Base

    Base.metadata.create_all(engine)
    assert migrate(engine) == CURRENT_SCHEMA_VERSION

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version FROM schema_version")).scalar_one() == CURRENT_SCHEMA_VERSION
