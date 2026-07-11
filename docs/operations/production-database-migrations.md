# Build 176 — Production Database Migration Gate

## Deployment rule
Database migrations run as an explicit release step before new application instances receive traffic.

## Required checks
1. `alembic upgrade head` succeeds against an empty PostgreSQL database.
2. The same command succeeds against a copy of the current development schema.
3. `alembic current` reports the expected head revision.
4. Application startup does not silently create or alter production tables.
5. A backup is confirmed before destructive or irreversible migrations.
6. Downgrade or forward-fix instructions are documented for each high-risk revision.

## Operational sequence
- Put the release in maintenance mode when required.
- Create and verify a database backup.
- Run migrations from a single release job.
- Run schema and application smoke checks.
- Start the new application release.
- Record the migration revision and release commit.

## Failure behavior
If migration or verification fails, application deployment stops and traffic remains on the prior release.
