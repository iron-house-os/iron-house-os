# Iron House OS

Iron House OS is a civil-construction operating system for projects, documents, drawing intelligence, estimates, supplier quotes, RFQ packages, bids, equipment, tenders, and municipality workflows.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic Settings
- Database: PostgreSQL
- Runtime: Docker Compose, Nginx, persistent Docker volumes
- Quality: GitHub Actions, pytest, Ruff, TypeScript, Vitest

## Local Development

1. Optional: copy environment files for local overrides.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Start the development stack.

```bash
docker compose up --build
```

3. Open the services.

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Readiness: http://localhost:8000/readiness
- Administrator diagnostics: http://localhost:8000/api/v1/operations/diagnostics

Backend without Docker:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Frontend without Docker:

```bash
cd frontend
npm install
npm run dev
# After installing Chromium with Playwright:
npm run build && npm run test:e2e
```

## Production Release

Build 207 added the production Compose stack. Builds 208–211 add database-backed sessions, role permissions, login abuse safeguards, and administrator-assisted recovery. Build 209 adds the complete Alembic baseline and verified database-plus-upload recovery bundles. Build 212 adds private S3-compatible storage and verified scheduled-backup retention while preserving the controlled local-volume option. Builds 213–215 add operational diagnostics, browser/mobile/accessibility gates, and an integrity-bound production-candidate package. Build 216 adds the approved, fail-closed Toronto live-cutover configuration and verified off-host recovery workflow.

```bash
cp .env.production.example .env.production
# Replace every placeholder secret in .env.production before continuing.
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build --wait
set -a && source .env.production && set +a
python scripts/release_smoke.py --base-url http://127.0.0.1:8080 --full
scripts/backup.sh --output "/secure/off-host/ihos-$(date -u +%Y%m%dT%H%M%SZ)"
```

The smoke test expects `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`. It signs in through the application before testing protected APIs. Full mode creates clearly named validation records; omit `--full` for a read-only health, login, and application-shell check.

See [the release runbook](docs/deployment.md) before exposing IHOS outside a trusted network. A public deployment must terminate HTTPS upstream, schedule off-host recovery bundles, and regularly confirm the automated restore drill remains green.

The production appearance is protected by the [Iron House OS visual design lock](docs/visual-design-lock.md). New features must follow the existing gold, silver, black, and charcoal visual system; significant restyling requires explicit owner approval.

The approved Build 216 DigitalOcean configuration and operator procedure are documented in [Build 216](docs/builds/BUILD_216.md). The live script requires the exact merged commit, the matching GitHub release-evidence artifact, protected provider credentials, matching DNS, and an explicit go flag.

## Core Application Areas

- Project workspaces and project-scoped launchers
- Document library, integrity metadata, signed downloads, and audit events
- Civil PDF ingestion, quantity candidates, and review flags
- Quantity takeoff and estimate handoff
- Estimate workspace and workbook generation
- Supplier quote comparison and explicit quote selection
- Supplier-specific RFQ packages and preview-only communication workflows
- Tender, bid-readiness, municipality, supplier, and equipment modules

## License

MIT
