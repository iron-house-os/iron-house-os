# Build 231 — Email Identity Domain Cleanup

## Task Card

- **Lead function:** Administration and Communications
- **Supporting functions:** System Governance, Security, Estimating, Operations
- **Owner:** Jeremie Peters
- **Priority:** High
- **Status:** Ready
- **Environment:** Development only
- **Approval gate:** Production backup, reviewed dry-run evidence, explicit apply approval

## Objective

Make `ironhousecontracting.com` the canonical email domain for current Iron House
accounts, employee identities, supplier contacts and active communication routing.
The live hostname `os.ironhousecivil.com` remains unchanged.

## Verified

- The canonical company email domain is `ironhousecontracting.com`.
- The approved IHOS hostname is `os.ironhousecivil.com` and is separate from company
  email identity.
- Current authentication tokens contain both the account email and a session version.
- User accounts and employee records have unique email constraints.
- Production is not modified by this build branch.

## Assumptions

- Existing password hashes, roles, account IDs and employee IDs must remain unchanged.
- Active RFQ draft routing should use the canonical domain after migration.
- Historic authorship, submission, signature, source-email and append-only audit evidence
  must retain the value recorded at the time of the event.

## Included

- Dry-run-by-default operator tool.
- Case-insensitive collision detection before any write.
- One-transaction updates to:
  - user accounts;
  - employee identities;
  - supplier contacts;
  - supplier routing metadata;
  - active RFQ recipient and Gmail draft routing;
  - field alert email recipients.
- Session-version increments for migrated user accounts.
- Removal of login throttles for both retired and canonical account addresses.
- Bootstrap protection that refuses the retired email domain.
- Development, backend and browser test identities updated to the canonical domain.

## Excluded

- DNS or hostname changes.
- Mailbox creation, Google Workspace administration or email forwarding.
- Rewriting financial provenance, submitted-by values, digital signatures, imported-by
  values or append-only document-audit actors.
- Production execution, deployment or merge.

## Review Gates

| Gate | Required evidence | Status |
|---|---|---|
| Source review | No retired-domain literals in current test identities | Complete |
| Migration review | Dry run, collision refusal, idempotence and history preservation | Complete |
| Test review | Backend, frontend and build checks | Complete |
| Production approval | Backup plus reviewed dry-run JSON | Blocked pending approval |

## Open Items

- Confirm the production dry-run inventory and resolve any collision it reports.
- Confirm `/etc/iron-house-os/production.env` uses the canonical bootstrap administrator
  email before the next backend restart.
- Approve or reject production application after reviewing the backup and dry-run.

## Build Log

- **2026-07-24:** Task card opened; source inventory separated email identities from the
  approved web hostname.
- **2026-07-24:** Migration service, packaged operator command, collision controls,
  session invalidation and bootstrap-domain guard implemented in development.
- **2026-07-24:** Verification completed: 143 backend tests, 21 frontend tests,
  TypeScript lint, frontend production build, Ruff and the 13-file visual-design lock
  passed. One existing Pydantic warning and one existing frontend chunk-size warning
  remain non-blocking.
