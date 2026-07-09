# IHOS MVP API Inventory

## System

- `GET /health`
- `GET /readiness`

## Projects

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/archive`
- `GET /api/v1/projects/{project_id}/dashboard`
- `GET /api/v1/projects/{project_id}/readiness`

## Takeoff

- `POST /api/v1/takeoff/summarize`
- `POST /api/v1/takeoff/engine`
- `POST /api/v1/takeoff/save`
- `GET /api/v1/takeoff/project/{project_id}`
- `GET /api/v1/takeoff/{takeoff_id}`

## Estimates

- `GET /api/v1/estimates/rate-library`
- `POST /api/v1/estimates/line-item`
- `POST /api/v1/estimates/handoff`
- `POST /api/v1/estimates/workspace`
- `GET /api/v1/estimates/workspace/project/{project_id}`
- `GET /api/v1/estimates/workspace/{workspace_id}`
- `POST /api/v1/estimates/summary`
- `POST /api/v1/estimates/workbook`

## RFQ automation

- `POST /api/v1/rfq-automation/recommend`
- `POST /api/v1/rfq-automation/linkage`
