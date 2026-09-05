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

The backend is a FastAPI service with PostgreSQL persistence through SQLAlchemy. Docker Compose provides the application and PostgreSQL services. The API currently exposes health, system status, and candidate CRUD/read endpoints.

### Development

```bash
pip install -e '.[test]'
pytest
uvicorn tradegpt.app:app --reload --port 8080
```

### Docker

Set `POSTGRES_PASSWORD` outside source control, then run:

```bash
docker compose up -d --build
```

The service is intentionally not configured for broker execution.

## Scheduled scans

Production schedule is limited to:

- 08:00 ET — Daily Sniper Discovery
- 10:15 ET — V2 Qualification
- 12:30 ET — Midday Second-Wave Discovery

## Data integrity

Decision-critical inputs must be timestamped and verified. Missing or stale inputs must produce `DATA_NOT_VERIFIED` and block `TRADE_READY`.

## Development status

The deterministic core, state machine, scoring gates, audit ledger, persistent candidate store, FastAPI runtime, Docker foundation, and automated tests are implemented. Market-data adapters, scan orchestration, forward-test/learning ledger, mobile PWA, and NAS deployment validation remain before production readiness.
