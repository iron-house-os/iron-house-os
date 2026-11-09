# Builds 36-50 Web App MVP Bridge

Builds 36-50 connect the backend MVP path to frontend clients, reusable panels, CI, Docker, and deployment readiness.

## Build register

- Build 36: Project readiness frontend API client.
- Build 37: Takeoff persistence frontend API client.
- Build 38: Estimate workspace frontend API client.
- Build 39: RFQ linkage frontend API client.
- Build 40: Project readiness panel.
- Build 41: Estimate workspace save panel.
- Build 42: RFQ linkage panel.
- Build 43: Hardened CI workflow.
- Build 44: Backend Dockerfile.
- Build 45: Frontend Dockerfile.
- Build 46: Frontend Nginx SPA config.
- Build 47: Docker Compose health check updates.
- Build 48: Deployment checklist.
- Build 49: MVP test plan.
- Build 50: MVP bridge documentation.

## Result

IHOS now has the structure for a working internal web app:

1. Project creation and workspace.
2. Takeoff engine.
3. Takeoff persistence.
4. Estimate handoff.
5. Estimate workspace persistence.
6. RFQ package draft linkage.
7. Project readiness checks.
8. Frontend clients and panels for the new workflow endpoints.
9. CI checks.
10. Docker and deployment documentation.

## Remaining before first live use

- Wire the new panels into the most relevant routed pages.
- Confirm database migrations/schema cover all existing SQLAlchemy models.
- Run CI and fix any lint/test failures.
- Configure production environment variables.
- Add authentication/permissions before exposing outside the company.
- Add real file upload/storage integration for drawings and bid documents.
