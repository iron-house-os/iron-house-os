# Build 213 — Operational observability and incident readiness

Build 213 adds an administrator-only operational view and a practical incident-response contract without sending events to an external service.

## Runtime visibility

- Every HTTP response carries an `x-request-id`; a caller-supplied ID is preserved for trace correlation.
- Every completed request emits one structured JSON log event with method, path, status, duration, and request ID. Query strings, bodies, cookies, and authorization material are excluded.
- The process retains a bounded 100-request diagnostic window. It reports status-class counts, server errors, maximum duration, and recent request metadata.
- `GET /api/v1/operations/diagnostics` combines live database/storage readiness, bounded traffic observations, and durable audit totals.
- `GET /api/v1/operations/security-events` exposes recent authentication, recovery, password, and access-denial events.
- Both operations endpoints are fail-closed to the administrator role. Denied access is written to the security audit stream.

The in-process traffic window resets on process restart and is diagnostic context, not durable monitoring. Durable security events remain in the configured audit store. External alert delivery is intentionally deferred until an approved monitoring destination exists.

## Operator response

Use [incident response](../operations/incident-response.md), [rollback](../operations/rollback.md), and [recovery](../operations/recovery.md) for the supported decision and verification paths.
