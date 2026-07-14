# Build 208 — individual user authentication

## Outcome

IHOS now protects business APIs with database-backed user accounts and signed HTTP-only sessions. The web app presents its own responsive login screen, supports logout and session expiry, and records document actors from the authenticated account rather than client-supplied identity headers.

## Included

- salted PBKDF2-SHA256 password storage with constant-time verification
- signed, expiring, HTTP-only, SameSite session cookies
- active-account and session-version checks on every protected request
- administrator APIs to create, list, update, deactivate, and reset user accounts
- forced session invalidation after role changes, deactivation, or password reset
- one-time bootstrap administrator creation from production secrets
- frontend login, current-user, logout, and automatic expired-session handling
- production smoke coverage that signs in before the project-to-drawing path
- authenticated document-audit actor identity

## Security boundary

The application shell and readiness probes remain public so infrastructure can serve the login page and monitor health. Every `/api/v1` business route is session-protected. The authentication capability endpoint and login route are public by design.

## Known limits

- Module permissions are not yet fully separated by role; account administration and document-audit permissions are role-enforced first.
- Login throttling, multi-factor authentication, and email password recovery are not included.
- A deployment still requires upstream HTTPS, protected host access, backups, and secret rotation.
- The repository still needs a complete Alembic baseline; the idempotent schema bootstrap creates missing model tables.
