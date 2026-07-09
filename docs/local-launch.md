# Local Launch Guide

## Prerequisites

- Docker Desktop or Docker Engine
- Node 22 for frontend-only local work
- Python 3.12 for backend-only local work

## Docker launch

```bash
docker compose up --build
```

Then check:

```bash
python scripts/smoke_check.py http://localhost:8000
```

Open:

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`
- Readiness: `http://localhost:8000/readiness`

## Frontend-only launch

```bash
cd frontend
npm ci
npm run dev
```

## Backend-only launch

```bash
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Stop services

```bash
docker compose down
```
