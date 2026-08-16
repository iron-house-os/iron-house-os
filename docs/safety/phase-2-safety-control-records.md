# Safety control records

High-risk permit readiness, corrective actions, and emergency action cards are authenticated database records in the Safety Operations module.

## Controls

- New permits always start `blocked`; a foreperson or manager must record verification evidence before marking them `ready`.
- Corrective actions start `open`; evidence is required for `verification` and `closed` states.
- Every status transition records the prior state, new state, actor, timestamp, and evidence.
- Employee and operator portal users cannot create or verify these control records.
- Emergency cards are operational information only. The responsible supervisor must confirm the site details with the crew whenever conditions change.

These workflows preserve the approved Iron House interface and do not publish new safety policy or regulatory conclusions.
