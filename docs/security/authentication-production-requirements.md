# Build 173 — Production Authentication Requirements

## Required capabilities
- Email and password login
- Logout and server-side refresh-token revocation
- Short-lived access tokens
- Rotating refresh tokens
- Password hashing using an approved adaptive algorithm
- Brute-force protection and authentication audit events
- Protected API dependencies and protected frontend routes
- Password reset workflow without account enumeration
- Forced replacement of bootstrap credentials

## Token rules
- Access tokens must expire in 30 minutes or less.
- Refresh tokens must be rotated on use and invalidated on logout.
- Tokens must contain user ID, organization ID, role and issued-at metadata.
- Production secrets must never be committed to the repository.

## Acceptance criteria
1. Anonymous requests to protected APIs return `401`.
2. Authenticated users can access only their organization.
3. Disabled users cannot obtain or refresh sessions.
4. Authentication failures emit structured audit events.
5. Frontend navigation redirects anonymous users to login.
6. Automated tests cover login, logout, refresh, expiry and invalid credentials.
