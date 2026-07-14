# Build 211 — login abuse protection and account recovery

## Outcome

Login failures are now throttled through persistent database state for both known and unknown email addresses. Five failed attempts lock that normalized login subject for 15 minutes by default, and even a correct password is rejected until the lock expires or an administrator begins recovery.

## Safeguards

- login subjects are stored in the throttle table as SHA-256 hashes rather than raw attempted addresses
- unknown accounts perform the same password-derivation work and receive the same generic rejection as known accounts
- lockout counters survive process restarts and are included in database backups
- `429 Too Many Requests` responses include `Retry-After` without disclosing whether an account exists
- `LOGIN_MAX_FAILED_ATTEMPTS` and `LOGIN_LOCKOUT_MINUTES` are bounded configuration values

## Administrator-assisted recovery

The existing administrator reset endpoint now starts a controlled recovery: it clears the login lock, invalidates every existing session, installs the temporary password, and marks the account as requiring a permanent password. The recovered user can sign in but cannot open any business module until completing `POST /api/v1/auth/change-password`. The web application presents that recovery form automatically.

New administrator-created users follow the same temporary-password path. There is no email recovery or externally delivered reset link in this build.

## Security audit

Login denial, lockout, successful login, administrator recovery, denied password change, successful password change, and business access blocked by a temporary password are appended to the durable audit stream. Events contain subject hashes, actor identity when authenticated, outcome, and request ID; passwords, cookies, session tokens, and request bodies are excluded.

## Known limits

- Throttling is per normalized email subject, not per network address or device.
- Multi-factor authentication and external identity providers remain future work.
