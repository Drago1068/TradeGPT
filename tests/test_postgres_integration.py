import os

import pytest
from sqlalchemy import inspect, text

from tradegpt.db import Base, make_engine
from tradegpt.migrations import CURRENT_SCHEMA_VERSION, migrate


pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL integration tests require DATABASE_URL=postgresql...",
)


def test_postgres_migration_is_idempotent_and_persists_schema_version():
    engine = make_engine()

    assert migrate(engine) == CURRENT_SCHEMA_VERSION
    assert migrate(engine) == CURRENT_SCHEMA_VERSION

    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        assert {"schema_version", "candidates", "audit_events", "learning_records"}.issubset(tables)
        assert connection.execute(text("SELECT version FROM schema_version")).scalar_one() == CURRENT_SCHEMA_VERSION


def test_postgres_migration_stamps_existing_schema():
    engine = make_engine()

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS schema_version"))
        Base.metadata.create_all(connection)

    assert migrate(engine) == CURRENT_SCHEMA_VERSION

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version FROM schema_version")).scalar_one() == CURRENT_SCHEMA_VERSION


def test_postgres_migration_rejects_newer_schema_version():
    engine = make_engine()

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS schema_version"))
        connection.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        connection.execute(
            text("INSERT INTO schema_version(version) VALUES (:version)"),
            {"version": CURRENT_SCHEMA_VERSION + 1},
        )

    with pytest.raises(RuntimeError, match="newer than application"):
        migrate(engine)
