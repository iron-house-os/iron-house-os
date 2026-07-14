# Production cutover checklist

No step in this checklist authorizes infrastructure spend, DNS changes, credential sharing, or external communication. Those actions require Jeremie’s explicit approval.

## Go/no-go prerequisites

- [ ] Approved host, region, budget, domain, TLS termination, backup destination, and monitoring destination are recorded.
- [ ] Named cutover operator, approver, rollback owner, and maintenance window are recorded in UTC.
- [ ] Immutable application image digests and the release-candidate commit match the evidence bundle.
- [ ] CI, browser/mobile/accessibility, production-stack smoke, migration, backup, and restore gates passed for that commit.
- [ ] Production secrets are supplied through the approved secret store and are absent from files, logs, shell history, and evidence.
- [ ] A verified pre-cutover recovery point exists off host; its restore drill and expected recovery window are recorded.
- [ ] Incident, rollback, and recovery runbooks are open and the last known-good release is deployable.

Any unchecked prerequisite is a no-go.

## Cutover sequence

1. Announce the approved maintenance state through the separately approved communication plan.
2. Freeze writes, record UTC time, and create/verify the final pre-cutover backup.
3. Deploy the exact approved image/configuration and apply migrations once.
4. Require green `/health` and `/readiness` before routing user traffic.
5. Run authenticated smoke, representative read/write, document upload/download, diagnostics, and desktop/mobile browser checks.
6. Complete the operator acceptance record. Route traffic only after explicit go approval.
7. Create a verified post-cutover backup and begin the observation window.

## Abort conditions

Abort and follow the rollback runbook for migration uncertainty, failed readiness, authentication failure, data-integrity mismatch, failed upload/download, unapproved configuration drift, or missing evidence. Preserve logs and do not improvise destructive database changes.
