# Durable Workflow Drafts

Issue: #246

IHOS saves unfinished, user-entered workflow data so navigating away, refreshing, or briefly losing the network does not erase work.

## Current coverage

- Purchase order requests
- Supplier quote comparison
- Estimating
- `MVP Workflow` Resume unfinished work queue

## Persistence rules

- The IHOS database is the source of truth for drafts.
- Browser storage is a short-term recovery buffer only. It is removed after the same payload reaches IHOS.
- Draft reads, updates, completion, and cancellation are scoped to the authenticated account that created the draft.
- Saves carry an expected revision. A stale revision returns HTTP `409` instead of overwriting newer work from another session.
- Completed and cancelled drafts leave the Resume queue but remain in the database for auditability.
- A draft is not an approval, award, purchase order, contract, safety record, or other commitment.

## API

- `POST /api/v1/workflow-drafts`
- `GET /api/v1/workflow-drafts`
- `GET /api/v1/workflow-drafts/{id}`
- `PATCH /api/v1/workflow-drafts/{id}`
- `POST /api/v1/workflow-drafts/{id}/complete`
- `POST /api/v1/workflow-drafts/{id}/cancel`

Draft payloads have a workflow type and schema version so future form changes can be migrated deliberately.
