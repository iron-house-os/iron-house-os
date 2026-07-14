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
```

## Production Release

Build 207 adds a production Compose stack with a compiled Nginx frontend, same-origin API proxying, startup migrations and schema bootstrap, PostgreSQL persistence, document and audit persistence, runtime readiness probes, temporary browser login protection, and a full release smoke test.

```bash
cp .env.production.example .env.production
# Replace every placeholder secret in .env.production before continuing.
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build --wait
python scripts/release_smoke.py --base-url http://127.0.0.1:8080 --full
```

The smoke test expects `IHOS_ADMIN_USERNAME` and `IHOS_ADMIN_PASSWORD` in the environment when the login gate is enabled. It creates clearly named validation records in full mode; omit `--full` for a read-only health and application-shell check.

See [the release runbook](docs/deployment.md) before exposing IHOS outside a trusted network. A public deployment must terminate HTTPS upstream and back up both persistent volumes.

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
