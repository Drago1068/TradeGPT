from __future__ import annotations

from sqlalchemy import inspect, text

from .db import Base

CURRENT_SCHEMA_VERSION = 2
MIGRATION_LOCK_KEY = 82746321


def _schema_tables() -> set[str]:
    return {"candidates", "audit_events", "learning_records", "scan_observations"}


def migrate(engine) -> int:
    """Apply the TradeGPT schema and return the resulting schema version.

    PostgreSQL deployments may start the API and worker simultaneously. A
    transaction-scoped advisory lock prevents concurrent bootstrap/migration.
    Existing version-1 databases are upgraded by creating the additive
    scan_observations table; historical candidate, audit and learning data are
    retained unchanged.
    """
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": MIGRATION_LOCK_KEY},
            )

        connection.execute(
            text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        )
        row = connection.execute(text("SELECT version FROM schema_version LIMIT 1")).first()
        version = int(row[0]) if row else 0

        if version > CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than application "
                f"version {CURRENT_SCHEMA_VERSION}"
            )

        existing = set(inspect(connection).get_table_names())
        if version == 0:
            if {"candidates", "audit_events", "learning_records"}.issubset(existing):
                version = 1
            else:
                Base.metadata.create_all(connection)
                version = 2

        if version == 1:
            ScanObservationRow = Base.metadata.tables["scan_observations"]
            ScanObservationRow.create(connection, checkfirst=True)
            version = 2

        if version != CURRENT_SCHEMA_VERSION:
            raise RuntimeError(f"migration stopped at unsupported schema version {version}")

        connection.execute(text("DELETE FROM schema_version"))
        connection.execute(
            text("INSERT INTO schema_version(version) VALUES (:version)"),
            {"version": version},
        )
        return version
