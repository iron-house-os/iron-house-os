# Build 209 — migration and recovery baseline

## Outcome

IHOS now has one authoritative Alembic revision for the complete current application schema and a checked database-plus-upload recovery path. Clean databases are created by Alembic. Complete unversioned Build 208 databases are adopted without recreating tables or losing records, while partial unversioned schemas fail with an actionable error.

## Included

- complete schema baseline for every current SQLAlchemy model, constraint, and index
- schema-drift test comparing a clean Alembic database with current model metadata
- SQLite and PostgreSQL upgrade tests proving Build 208 records survive baseline adoption
- rejection test for unsafe partial unversioned schemas
- startup readiness tied to the exact Alembic revision
- consistent PostgreSQL and `/app/data` recovery bundles with checksums and schema metadata
- destructive restore confirmation, bundle verification, and a default pre-restore safety backup
- disposable release drill that restores a database record and uploaded PDF, then verifies the file checksum

## Safety boundary

Alembic is the only deployed schema authority. The legacy SQL schema and SQLAlchemy `create_all` compatibility helper are not part of runtime startup. Baseline downgrade is deliberately blocked because the revision may have adopted a pre-existing Build 208 database and cannot safely infer ownership of its tables.

Recovery bundles do not contain environment files or application secrets. Operators must store completed bundles off-host and maintain the matching production secret key separately.

## Known limits

- The included scripts target the single-node Docker Compose deployment.
- Backup scheduling, off-host retention, encryption at rest, and retention policy remain deployment responsibilities.
- Build 209 proves logical PostgreSQL plus local application-data recovery; it does not add cross-region replication or managed object storage.
