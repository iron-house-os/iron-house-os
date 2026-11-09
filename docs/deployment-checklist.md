# IHOS Deployment Checklist

## Required services

- Backend FastAPI service
- Frontend Vite/React service
- PostgreSQL database
- Persistent document/file storage
- Environment variable management

## Required environment

Backend:

- `DATABASE_URL`
- `BACKEND_CORS_ORIGINS`
- API prefix from config

Frontend:

- `VITE_API_BASE_URL`

## Pre-deploy checks

1. Run backend lint and tests.
2. Run frontend lint, tests, and build.
3. Confirm `/health` returns `ok`.
4. Confirm `/readiness` returns `ready`.
5. Confirm `/api/v1/projects` loads.
6. Confirm project creation works.
7. Confirm takeoff engine runs.
8. Confirm estimate handoff runs.
9. Confirm project readiness endpoint runs.

## First production target

Deploy as a private internal web app first. Do not expose public registration, public file upload, or supplier-facing RFQ links until auth, permissions, audit logging, and storage controls are complete.
