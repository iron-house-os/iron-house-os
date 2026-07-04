# Iron House OS

Iron House OS is a civil construction operating system foundation for projects, RFQs, suppliers, bids, documents, equipment, tenders, and future AI-assisted workflows.

This repository is Phase 1: a production-ready scaffold with clean architecture, developer tooling, Docker support, API documentation, placeholder application modules, database models, and seed data. It intentionally does not implement business logic yet.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic Settings
- Database: PostgreSQL
- Tooling: Docker Compose, GitHub Actions, pytest, Ruff, ESLint

## Repository Structure

```text
.
|-- frontend/              # React dashboard shell
|-- backend/               # FastAPI application
|-- database/              # SQL schema and seed data
|-- docker/                # Container support files
|-- docs/                  # Architecture and development notes
|-- scripts/               # Developer helper scripts
|-- tests/                 # Backend smoke tests
|-- .github/workflows/     # CI
|-- docker-compose.yml
|-- LICENSE
`-- README.md
```

## Quick Start

1. Optional: copy environment files if you want local overrides.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Start the local stack.

```bash
docker compose up --build
```

3. Open the apps.

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Database migrations:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Placeholder Modules

The frontend includes navigation and placeholder pages for:

- Dashboard
- Projects
- RFQ Builder
- Supplier Database
- Estimating
- Tender Tracker
- Document Library
- Equipment
- Reporting
- Settings

The backend includes placeholder REST routes for:

- `/projects`
- `/suppliers`
- `/rfqs`
- `/bids`
- `/documents`
- `/equipment`
- `/users`
- `/auth`

## Data Model Foundation

The backend and schema define these initial entities:

- Project
- Supplier
- Contact
- RFQ
- Quote
- Bid
- Drawing
- Takeoff
- Equipment
- Employee
- Municipality
- Tender

## Phase 1 Scope

Included:

- Dockerized development environment
- Environment-driven configuration
- Structured logging
- Centralized error handling
- Health endpoint
- API documentation
- Example seed data
- GitHub Actions workflow
- Clean service boundaries for future AI agents

Not included yet:

- RFQ package generation
- Supplier CRM workflows
- BC Bid scraping
- Drawing ingestion
- Quantity takeoff automation
- Bid engine business logic
- Municipality standards intelligence
- Google Drive or Gmail integration

## License

MIT
