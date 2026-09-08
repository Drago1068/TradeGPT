from sqlalchemy import inspect, text

from tradegpt.db import Base, make_engine
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

    Base.metadata.create_all(engine)
    assert migrate(engine) == CURRENT_SCHEMA_VERSION

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version FROM schema_version")).scalar_one() == CURRENT_SCHEMA_VERSION


def test_migrate_rejects_newer_schema_version():
    engine = make_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        connection.execute(text("INSERT INTO schema_version(version) VALUES (:version)"), {"version": CURRENT_SCHEMA_VERSION + 1})

    try:
        migrate(engine)
    except RuntimeError as exc:
        assert "newer than application" in str(exc)
    else:
        raise AssertionError("migrate() must reject a database newer than the application")


def test_make_engine_enables_connection_liveness_checks():
    engine = make_engine("sqlite:///:memory:")

    assert engine.pool._pre_ping is True
