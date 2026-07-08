# IHOS MVP Test Plan

## Smoke test

1. Start database, backend, and frontend.
2. Open frontend.
3. Create a project.
4. Register at least one document.
5. Run quantity takeoff engine.
6. Save takeoff to project.
7. Send takeoff items to estimating.
8. Save estimate workspace.
9. Generate RFQ package drafts.
10. Run project readiness.

## Backend endpoints to verify

- `GET /health`
- `GET /readiness`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `POST /api/v1/takeoff/engine`
- `POST /api/v1/takeoff/save`
- `POST /api/v1/estimates/handoff`
- `POST /api/v1/estimates/workspace`
- `POST /api/v1/rfq-automation/linkage`
- `GET /api/v1/projects/{project_id}/readiness`

## Acceptance criteria

- No manual database edits required.
- Project data survives page reload.
- Saved takeoffs appear in project readiness.
- Saved estimates appear in project readiness.
- RFQ drafts are generated from takeoff or estimate scope.
- CI passes before deployment.
