# TradeGPT V2 — NAS Deployment Runbook

## Scope

This runbook targets the UGREEN NAS DXP4800 using Docker Compose. GitHub is the source of truth; the NAS must not become the canonical copy of application code.

## Safety boundary

The initial production system is decision-support only. Broker order submission is disabled. Do not expose PostgreSQL or the worker directly to the Internet.

## Initial deployment

1. Install Docker/Compose support on the NAS.
2. Clone the `Drago1068/TradeGPT` repository into a deployment directory.
3. Copy `.env.example` to `.env`.
4. Replace the placeholder `POSTGRES_PASSWORD` with a strong secret. Never commit `.env`.
5. Keep `MARKET_DATA_PROVIDER=none` until a real provider is selected, configured, tested, and explicitly promoted.
6. Start with `docker compose up -d --build`.
7. Verify `docker compose ps` shows the database healthy and the application healthy.
8. Verify the application `/health` endpoint before exposing the UI through a secure access layer.
9. Verify `/ready` before treating the system as operational.

## Data persistence

The PostgreSQL volume `tradegpt_pgdata` is persistent application state. Do not delete it during routine upgrades. Application code is disposable and must be recoverable from GitHub.

Backups must include the PostgreSQL database, not merely the container image or repository checkout. Test restoration before relying on a backup.

## Upgrade procedure

1. Confirm the current deployment is healthy.
2. Record the running Git commit SHA.
3. Take a PostgreSQL backup/snapshot.
4. Pull the approved GitHub revision.
5. Rebuild and restart with `docker compose up -d --build`.
6. Confirm migrations complete and `/ready` is healthy.
7. Confirm the three production scan schedules remain configured.
8. Confirm no broker execution capability has been enabled.

## Rollback

Rollback means returning application code to the last known-good Git revision and restoring database state only when a migration is not backward-compatible. Never delete the production database volume as a rollback shortcut.

## Recovery test

At least once before production reliance, restore a backup into an isolated PostgreSQL instance and verify that candidates, audit events, learning records, and schema version are readable.

## Monitoring

Monitor:
- API health/readiness
- worker restarts
- database health
- missed or delayed scans
- `SCAN_NO_PLAN` events
- `DATA_NOT_VERIFIED` decisions
- provider failures and latency
- disk capacity and PostgreSQL backup success

## Market-data promotion gate

A real provider is not production-ready merely because an HTTP request succeeds. Promotion requires validated timestamps, freshness, symbol identity, required fields, source metadata, failure behavior, and deterministic qualification tests. Until those gates pass, the system must remain fail-closed.
