# Build 233 — Identity Governance Centre

## Task card

- **Status:** Development complete; verification pending
- **Owner:** Iron House OS build program
- **Environment:** Development only
- **Approval boundary:** No production deployment and no merge without approval

## Verified

- User accounts already record role, active state, last sign-in, and forced-password-change state.
- User administration is restricted to the administrator role.
- The approved Settings page can host governance information without changing the locked navigation or application shell.

## Assumption

- Seven days without a first sign-in warrants review.
- Ninety days without a sign-in warrants review.
- One active administrator is an access-continuity risk; zero is critical.

## Delivered

- Administrator-only identity governance snapshot API.
- Canonical and legacy domain checks.
- Active-administrator coverage check.
- Pending password change, never-used, and stale-account checks.
- Case-insensitive duplicate identity detection.
- Settings-based Identity Governance Centre with summary, findings, and account review reasons.
- Responses exclude password hashes and session versions.

## Open items

- Thresholds require management approval before they become formal policy.
- Account review decisions and evidence are not yet persisted.
- Production identity data has not been inspected or changed.

## Automation recommendation

Run the governance snapshot weekly and notify administrators only when findings change or critical findings exist.
