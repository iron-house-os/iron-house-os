# Build 218: Production Tender Tracker repair

## Root cause

The original Phase 1 tender table used the status `watching`. The later Tender Intake workflow replaced it with `new`, but the Build 209 baseline adopted populated databases without translating existing rows. Reading a legacy row raised a status-enum error and returned HTTP 500 from `GET /api/v1/tenders`.

The Build 217 browser audit did not detect the failure because it mocked every API response. The production-stack smoke path also skipped Tender Tracker.

## Repair

- Migrate legacy tender statuses to the current workflow and add a database check constraint.
- Keep a defensive legacy-status adapter in the API so one old row cannot crash the list.
- Require all core runtime tables and valid tender statuses before `/readiness` reports ready.
- Make both read-only and full authenticated release smoke tests query Tender Tracker and Equipment.
- Expose the deployed commit SHA as `release_id` in readiness output.

## Streamlined production topology

- Canonical source: `iron-house-os/iron-house-os`, branch `main`.
- Canonical production host: `iron-house-os-prod-1` (DigitalOcean droplet `584847629`).
- Public endpoint: `https://os.ironhousecivil.com`.
- Any Codex Universal droplet is a temporary repair workspace, must not receive production traffic, and must not be treated as a second production environment.

## Release rule

A release is not accepted until the exact commit is deployed to the canonical production host and the authenticated smoke test passes against both the loopback service and the public domain. A frontend-only tab audit is not production acceptance.
