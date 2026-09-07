from __future__ import annotations

from sqlalchemy import inspect, text

from .db import Base

CURRENT_SCHEMA_VERSION = 1
MIGRATION_LOCK_KEY = 82746321


def _schema_tables() -> set[str]:
    return {"candidates", "audit_events", "learning_records"}


def migrate(engine) -> int:
    """Apply the TradeGPT schema and return the resulting schema version.

    Version 1 is the initial relational schema. Existing databases created by
    the pre-migration ``create_all`` bootstrap are safely recognized and stamped
    rather than attempting to recreate their tables. Future changes should be
    added as explicit versioned migrations here.

    PostgreSQL deployments may start the API and worker simultaneously. A
    transaction-scoped advisory lock prevents both processes from attempting the
    first schema bootstrap or a future migration at the same time. SQLite keeps
    its existing single-process test path without using PostgreSQL-specific SQL.
    """
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": MIGRATION_LOCK_KEY},
            )

        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_version "
                "(version INTEGER NOT NULL)"
            )
        )
        row = connection.execute(text("SELECT version FROM schema_version LIMIT 1")).first()
        version = int(row[0]) if row else 0

        if version > CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than application "
                f"version {CURRENT_SCHEMA_VERSION}"
            )

        if version < 1:
            existing = set(inspect(connection).get_table_names())
            if _schema_tables().issubset(existing):
                version = 1
            else:
                Base.metadata.create_all(connection)
                version = 1

            connection.execute(text("DELETE FROM schema_version"))
            connection.execute(
                text("INSERT INTO schema_version(version) VALUES (:version)"),
                {"version": version},
            )

        return version
