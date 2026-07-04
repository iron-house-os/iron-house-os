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

The SQL files in `database/` provide a clear starting schema. Alembic is included for application-managed migrations as models evolve.

## Phase 2 Guidance

Keep first business workflows narrow and observable. Add tests for route behavior, data transitions, permissions, and any integration adapter before introducing automation.
