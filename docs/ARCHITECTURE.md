# Trade GPT V2 — System Architecture

## Source of Truth

GitHub is the canonical source repository. The production runtime is deployable from the repository and must not contain irreplaceable state.

## Runtime Target

Primary production host: UGREEN NAS DXP4800.

Containerized services are preferred so the system can be moved to another x86-64 host without rewriting the application.

Initial target services:
- Web/PWA frontend
- API service
- Scanner/worker service
- Scheduler/orchestrator
- PostgreSQL database

Redis is optional and should not be introduced until a measured need exists.

## Logical Components

1. Market Data Adapter Layer
2. Discovery Engines
3. Candidate Normalizer
4. Candidate/State Store
5. Qualification Engine
6. Deterministic Risk Engine
7. Portfolio State
8. Alert/Notification Layer
9. Trade Journal
10. Learning Ledger
11. Missed Opportunity Ledger
12. Model Registry/Router
13. Observability and Audit Log
14. Responsive PWA

## Separation of Concerns

Discovery may use broad heuristics and multiple research workers. Qualification and risk gates must be deterministic wherever practical. AI-generated reasoning cannot bypass hard risk or data gates.

## AI Model Architecture

Qwen, Perplexity, Claude, OpenAI models, or other models may be used as interchangeable research workers. Each output must carry model/provider, prompt version, timestamp, task, and confidence metadata. No model is a single point of failure or a mandatory approval authority.

## Scheduled Workflow

The production workflow is logically organized around three market-session scans:

1. 08:00 ET — Daily Sniper Discovery
2. 10:15 ET — V2 Qualification
3. 12:30 ET — Midday Discovery/Qualification

The exact scheduler implementation must support timezone-aware scheduling and record actual execution timestamps. Missed or delayed scans must be visible as system-health events.

## 08:00 Discovery

Broad candidate generation. Target a healthy candidate pipeline rather than only A+ opportunities. Produce discovery candidates with source evidence and initial scores.

## 10:15 Qualification

Re-evaluate existing candidates and new candidates. Advance candidates through WATCH/ARMED/TRIGGERED as evidence supports. Generate 0–2 BUY NOW recommendations only when TRADE READY hard gates pass.

## 12:30 Midday

Search for new catalysts, breakouts, reclaims, sector rotation, relative-strength changes, second-wave momentum, and candidates missed during the morning. Re-evaluate existing ARMED candidates.

## Persistence

Candidates survive between scans until they trigger, invalidate, expire, or are rejected. Scan results must not overwrite prior observations.

## Mobile/PWA

The frontend must be responsive. Mobile users can view dashboard state, candidates, active positions, risk, alerts, scan status, and system health. Administrative configuration can remain desktop-oriented.

## Security

Secrets must be injected through environment/configuration management and excluded from source control. Database and internal services must not be exposed directly to the public Internet. Remote access must use a secure access layer.

## Production Safety

Broker execution is disabled in the initial release. Market-data ingestion, analysis, paper/forward testing, and decision-support may operate independently from any future execution adapter.
