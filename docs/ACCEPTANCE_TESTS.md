# Trade GPT V2 — Acceptance Tests

The system is not production-ready until these gates pass.

## Architecture

- [ ] GitHub repository is the canonical source of truth.
- [ ] Runtime can be rebuilt from source.
- [ ] No production dependency on a single AI model.
- [ ] Broker execution is disabled by default.

## Discovery

- [ ] Discovery produces multiple candidates when market conditions support them.
- [ ] Discovery is not restricted to A+ setups.
- [ ] Fresh catalysts are not required for every candidate.
- [ ] Compression, continuation, reclaim, relative-strength and sector/sympathy setups can be discovered.
- [ ] Candidate observations persist across scans.

## State Machine

- [ ] DISCOVERED → WATCH works.
- [ ] WATCH → ARMED requires defined thesis and trigger.
- [ ] ARMED → TRIGGERED requires objective trigger evidence.
- [ ] TRIGGERED → TRADE READY requires every hard execution gate.
- [ ] Failed gates produce REJECTED or remain non-executable.
- [ ] Invalidated and expired candidates remain auditable.
- [ ] Every transition is timestamped and reason-coded.

## Risk

- [ ] Account equity is configurable.
- [ ] Position size is calculated from planned dollar risk and stop distance.
- [ ] 1% normal risk ceiling is enforced.
- [ ] 2% exceptional ceiling cannot activate accidentally.
- [ ] 5% portfolio heat is enforced.
- [ ] 3% daily loss limit is enforced.
- [ ] Minimum 2R execution requirement is enforced.
- [ ] Stop widening is impossible through normal workflow.
- [ ] Averaging down is unavailable.
- [ ] Chase protection is enforced.

## Data Integrity

- [ ] Every decision-critical input has a timestamp.
- [ ] Stale/unavailable inputs generate DATA NOT VERIFIED.
- [ ] DATA NOT VERIFIED blocks TRADE READY.
- [ ] Conflicting provider data is surfaced rather than silently reconciled.

## Learning

- [ ] Executed trades are immutable after close except through append-only corrections.
- [ ] MFE and MAE are recorded.
- [ ] Original score and state history are preserved.
- [ ] Missed qualified opportunities are recorded.
- [ ] False positives are measurable.
- [ ] Discovery lead time is measurable.
- [ ] Scan failures and missed scans are observable.

## Scheduling

- [ ] 08:00 ET discovery schedule is configured.
- [ ] 10:15 ET qualification schedule is configured.
- [ ] 12:30 ET midday schedule is configured.
- [ ] Actual start/end timestamps are recorded.
- [ ] Missed/delayed scans generate system-health events.

## Mobile

- [ ] Dashboard works on phone viewport.
- [ ] Candidate pipeline works on phone viewport.
- [ ] Active positions and risk are visible on mobile.
- [ ] Alerts link to the relevant candidate/trade.
- [ ] PWA installation is supported.

## NAS

- [ ] Docker Compose deployment works on DXP4800.
- [ ] Persistent database volume survives container restart.
- [ ] Configuration/secrets are external to source code.
- [ ] Database backup and restore procedure is tested.
- [ ] Internal services are not directly Internet-exposed.

## Forward Test

- [ ] System can run in paper/forward-test mode.
- [ ] No live order can be generated accidentally.
- [ ] Daily results can be replayed and evaluated.
- [ ] Strategy/model performance is measured without look-ahead leakage.

## Red-Team Exit Criteria

- [ ] A red-team review finds no critical path that can bypass risk gates.
- [ ] A red-team review finds no silent data substitution.
- [ ] A red-team review finds no state-loss path that causes candidates to disappear.
- [ ] A red-team review finds no automatic transition from discovery to live order.
