# Builds 31-35 MVP Readiness

This block moves IHOS from isolated tools toward a usable connected web app workflow.

## Build 31 - Takeoff Persistence

Added database-backed takeoff persistence using the existing `takeoffs` table.

Endpoints:

- `POST /api/v1/takeoff/save`
- `GET /api/v1/takeoff/project/{project_id}`
- `GET /api/v1/takeoff/{takeoff_id}`

## Build 32 - Estimate Workspace Persistence

Added estimate workspace storage using the existing `bids` table so estimates can be saved against projects.

Endpoints:

- `POST /api/v1/estimates/workspace`
- `GET /api/v1/estimates/workspace/project/{project_id}`
- `GET /api/v1/estimates/workspace/{workspace_id}`

## Build 33 - RFQ Linkage

Added RFQ draft generation from takeoff/estimate source items.

Endpoint:

- `POST /api/v1/rfq-automation/linkage`

## Build 34 - Project Readiness

Added project readiness scoring across tender dates, documents, takeoffs, estimates, and RFQ packages.

Endpoint:

- `GET /api/v1/projects/{project_id}/readiness`

## Build 35 - Deployment Readiness

Added system readiness endpoint.

Endpoint:

- `GET /readiness`

## Current web app status

IHOS now has the connected backend path for:

1. Project setup.
2. Document registration.
3. Takeoff generation.
4. Takeoff persistence.
5. Estimate handoff.
6. Estimate workspace persistence.
7. RFQ draft linkage.
8. Project readiness scoring.

Remaining MVP work is mostly frontend workflow polish, authentication hardening, deployment configuration, and real file upload/storage integration.
