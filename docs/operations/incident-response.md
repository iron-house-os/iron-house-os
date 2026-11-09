# Incident response

## Detect and classify

1. Record UTC time, operator, environment, symptom, and the response `x-request-id`.
2. Check `/health`. A failure means the API process or route is unavailable.
3. Check `/readiness`. A `503` identifies database or document-storage unavailability without disclosing credentials.
4. As an administrator, capture `/api/v1/operations/diagnostics` and relevant `/api/v1/operations/security-events` output.
5. Classify the incident as availability, data integrity, security, or performance. Treat suspected credential exposure or unauthorized access as security-critical.

## Contain

- Stop destructive user activity before changing data or configuration.
- Preserve application, proxy, database, and scheduled-backup logs with UTC timestamps.
- Do not paste cookies, passwords, tokens, connection strings, or uploaded document contents into the incident record.
- Disable a compromised user and rotate affected secrets through the approved operator channel.
- If the current release caused the incident, follow the rollback runbook.

## Recover and close

Use the recovery runbook for database or uploaded-file loss. Before reopening access, require `/health`, `/readiness`, authenticated smoke coverage, and a recorded operator decision. Record cause, impact, evidence, actions, and follow-ups. External notifications require explicit approval and an approved recipient list.
