# Build 178 — Staging Deployment Blueprint

## Target topology
- Managed PostgreSQL database
- Containerized FastAPI backend
- Static or containerized React frontend
- HTTPS on all public endpoints
- Separate staging secrets and database

## Required services
1. `iron-house-api-staging`
2. `iron-house-web-staging`
3. `iron-house-postgres-staging`
4. One-time migration/release job

## Release inputs
- Git commit SHA
- Backend production environment variables
- Frontend API base URL
- Database connection secret
- Authentication secret
- Allowed host and CORS origin values

## Health and readiness
- `/health` verifies process availability.
- A readiness endpoint must verify required dependencies without exposing secrets.
- Frontend deployment must fail when its production build fails.
- Backend deployment must fail when migrations or startup validation fail.

## Security requirements
- No default passwords
- No development debug mode
- Restricted database network access
- Automated TLS
- Secret rotation procedure
- Centralized application logs

## Deployment acceptance
The staging URL, backend URL, database revision, deployed commit and smoke-test result must be recorded in the Build 180 validation report.
