# Production cutover checklist

No step in this checklist authorizes infrastructure spend, DNS changes, credential sharing, or external communication. Those actions require Jeremie’s explicit approval.

## Build 216 approved plan

Jeremie approved Build 216 on 2026-07-15 with these limits:

- Host: DigitalOcean Basic Droplet, Toronto (`tor1`), 2 vCPU / 4 GiB
- Budget: maximum CAD 60 per month; no automatic paid upgrade
- Domain: `os.ironhousecivil.com`
- TLS: Let's Encrypt terminated by host Nginx
- Storage: private, versioned, encrypted AWS S3 in `ca-central-1`
- Recovery: daily Droplet backup plus verified off-host recovery bundles
- Monitoring: five-minute external checks for `/healthz` and `/readiness`
- Window: 2026-07-19 13:00–15:00 UTC
- Operator/approver: Jeremie Peters (`jeremie@ironhousecontracting.com`); rollback owner: Mac

This approval permits the listed hosting spend, DNS record, TLS issuance, monitoring, and live deployment. It does not permit exceeding the budget, substituting a provider/region, disabling recovery controls, or sharing secrets in source control or chat.

## Go/no-go prerequisites

- [ ] The target is the single canonical production host `iron-house-os-prod-1`; no repair workspace is tagged or routed as production.
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
5. Run authenticated smoke, including real Tender Tracker and Equipment reads, representative read/write, document upload/download, diagnostics, and desktop/mobile browser checks.
6. Complete the operator acceptance record. Route traffic only after explicit go approval.
7. Create a verified post-cutover backup and begin the observation window.

## Abort conditions

Abort and follow the rollback runbook for migration uncertainty, failed readiness, authentication failure, data-integrity mismatch, failed upload/download, unapproved configuration drift, or missing evidence. Preserve logs and do not improvise destructive database changes.
