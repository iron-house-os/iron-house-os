# Development

## Environment

Use `.env.example` files as the source of required variables. Local secrets should stay in `.env` files and out of version control.

## Backend Quality Gates

```bash
cd backend
ruff check .
pytest
```

## Frontend Quality Gates

```bash
cd frontend
npm run lint
npm run build
```

## Migrations

Alembic is the schema authority. Apply the current schema with `cd backend && alembic upgrade head`, and create reviewed Alembic revisions for model changes. Files in `database/` are legacy references and must not be used to initialize a runtime database.

## Phase 2 Guidance

Keep first business workflows narrow and observable. Add tests for route behavior, data transitions, permissions, and any integration adapter before introducing automation.
