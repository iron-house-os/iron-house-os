# Build 210 — module role permissions

## Outcome

Every protected API module now enforces one shared, fail-closed role matrix. Authentication alone no longer grants mutation access: viewers are read-only, estimators can operate estimating and bid workflows, operations managers can mutate every business module, and administrators additionally control user accounts.

## Role matrix

| Role | Business read | Estimating/project mutation | Equipment mutation | User administration |
| --- | --- | --- | --- | --- |
| `admin` | Yes | Yes | Yes | Yes |
| `operations_manager` | Yes | Yes | Yes | No |
| `estimator` | Yes | Yes | No | No |
| `viewer` | Yes | No | No | No |

User-account routes always require `administer`; all other `GET`, `HEAD`, and `OPTIONS` requests require `read`, while mutation methods require `write`. Unknown roles receive no permissions.

## Audit boundary

Every denied module action appends a `module_access` event to the configured durable audit stream with actor, role, module, method, path, requested permission, and request ID. Passwords, session cookies, request bodies, and other credentials are never recorded.

The authenticated permission summary is available at `GET /api/v1/auth/me/permissions`. The API remains authoritative even when a client does not pre-hide an unavailable action.
