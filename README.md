# TradeGPT V2 — Stock-First Decision Engine

TradeGPT V2 is a deterministic, risk-first market discovery and decision-support system. It is designed to surface asymmetric stock opportunities early while keeping execution gates strict, auditable, and data-verified.

## Core principles

- Stock-first; options and 0DTE remain disabled during the initial production phase.
- Discovery is broad; execution is ruthless.
- No fabricated or silently substituted market data.
- No automatic broker orders.
- No stop widening or averaging down.
- Every important candidate state change is auditable.

## Candidate lifecycle

`DISCOVERED → WATCH → ARMED → TRIGGERED → TRADE_READY → ENTERED → MANAGE → EXITED`

Terminal alternatives are `INVALIDATED`, `REJECTED`, and `EXPIRED`.

## Deterministic scoring

- Catalyst: 30%
- Technical structure: 30%
- Relative strength: 20%
- Liquidity: 20%

Score bands:

- 90–100: A+
- 82–89.99: A
- 74–81.99: WATCH
- 65–73.99: DISCOVERY
- Below 65: PASS

A score never bypasses hard execution gates.

## Risk controls

- Normal maximum trade risk: 1% of equity
- Exceptional A+ maximum: 2%
- Maximum portfolio heat: 5%
- Daily loss limit: 3%
- Minimum reward/risk: 2.0R
- Price floor: $3
- Minimum 30-day ADV: 500,000 shares and $5M dollar volume

Position size is calculated from the approved risk budget and stop distance.

## Runtime

The backend is a FastAPI service with PostgreSQL persistence through SQLAlchemy. Database startup uses an explicit schema migration/version marker, and PostgreSQL startup migration is protected by a transaction-scoped advisory lock so the API and worker can initialize concurrently without racing schema creation. Docker Compose provides the application, worker, and PostgreSQL services.

The API exposes health/readiness, system status, candidate, scan, scheduler, learning, forward-test, and outcome endpoints. The default runtime remains fail-closed until a real market-data provider and scan-plan provider are configured.

### Development

```bash
pip install -e '.[test]'
pytest
uvicorn tradegpt.app:app --reload --port 8080
```

### Docker

Copy `.env.example` to `.env` and set a strong `POSTGRES_PASSWORD` outside source control, then run:

```bash
docker compose up -d --build
```

The application image uses a multi-stage build, non-root runtime user, read-only filesystem, bounded temporary storage, health checks, resource limits, and offline installation from a dependency wheelhouse. The service is intentionally not configured for broker execution.

## Scheduled scans

Production schedule is limited to:

- 08:00 ET — Daily Sniper Discovery
- 10:15 ET — V2 Qualification
- 12:30 ET — Midday Second-Wave Discovery

The scheduler is timezone-aware, DST-aware, weekday-aware, and suppresses scans on configured NYSE full-day holidays.

## Data integrity

Decision-critical inputs must be timestamped and verified. Missing, stale, incomplete, or unconfigured provider data produces a fail-closed path and blocks `TRADE_READY`.

## Learning and forward testing

The system records candidate discovery, qualification, trade-readiness, trade/missed-opportunity status, and outcome metrics in a persistent learning ledger. Forward testing evaluates sequential close observations and explicitly avoids inventing intrabar execution outcomes.

## Development status

**Implemented:** deterministic core, state machine, scoring/risk gates, audit ledger, persistent stores, schema migration foundation, FastAPI runtime, scheduled worker, scan orchestration, market-data provider boundary, forward-test/learning ledger, Docker Compose foundation, CI tests, and container-build validation.

**Remaining before production:** real market-data adapter integration and credentials, real scan-plan/discovery engine, database failure/reconnect validation against PostgreSQL, NAS deployment/backup/restore validation, mobile PWA/UI, operational monitoring, and production acceptance testing.
