# Build 232 — Identity Cutover and Administrator Access Recovery

## Task Card

- **Lead function:** System Governance
- **Supporting functions:** Administration and Communications, Security
- **Owner:** Jeremie Peters
- **Priority:** High
- **Status:** Ready
- **Dependency:** Build 231 — Email Identity Domain Cleanup
- **Environment:** Development only
- **Approval gate:** Approved release, verified backup and explicit production recovery approval

## Objective

Provide a controlled server-console path to inspect and recover a canonical Iron House
administrator account when normal in-app administrator recovery is unavailable. Produce
cutover-readiness evidence without exposing passwords or changing production
automatically.

## Verified

- The canonical administrator identity uses `ironhousecontracting.com`.
- The production application remains at `https://os.ironhousecivil.com`.
- Password hashes, account IDs, roles and session versions are held in the IHOS database.
- Normal in-app password reset requires an already authenticated administrator.
- Build 231 provides the current-identity migration and must precede cutover verification.

## Assumptions

- The operator has authorised server-console and Docker access.
- The operator can securely enter a temporary password without placing it in command
  history or an evidence file.
- The recovered administrator will immediately complete the forced password change.

## Included

- Read-only administrator recovery inspection.
- Exact UUID confirmation before recovery.
- Canonical-domain, administrator-role and active-account eligibility checks.
- Interactive hidden password entry with confirmation.
- Existing-password reuse prevention.
- Session invalidation and login-throttle removal.
- Forced password change on next login.
- Non-secret JSON recovery evidence.
- Post-cutover readiness verification covering:
  - residual Build 231 identity changes;
  - canonical administrator presence, status and role;
  - production bootstrap email alignment;
  - completion of the forced password change.

## Excluded

- Email delivery, password-reset links or third-party identity providers.
- Browser credential entry or transfer of Safari session cookies.
- Account creation, account merging or role elevation.
- Production deployment, recovery execution or merge.

## Review Gates

| Gate | Required evidence | Status |
|---|---|---|
| Recovery security | Wrong account, role, domain, state, UUID and reused password blocked | Complete |
| Secret handling | Password absent from arguments and JSON evidence | Complete |
| Cutover readiness | Pending migration and forced password change reported | Complete |
| Regression | Backend, frontend, build and visual-lock checks | Complete |
| Production approval | Backup and explicit recovery authorisation | Blocked pending approval |

## Open Items

- Review and approve Build 231 before using Build 232 in production.
- Confirm the exact canonical administrator account ID from the read-only inspection.
- Establish an approved production maintenance and recovery window.
- Confirm secure evidence retention location and recovery operator.

## Build Log

- **2026-07-24:** Build 232 task card opened as a dependent development build.
- **2026-07-24:** Server-console inspection, guarded recovery, session invalidation,
  hidden password entry and cutover-readiness reporting implemented.
- **2026-07-24:** Verification completed: 152 backend tests, 21 frontend tests,
  TypeScript lint, frontend production build, Ruff and the 13-file visual-design lock
  passed. One existing Pydantic warning and one existing frontend chunk-size warning
  remain non-blocking.
