# Version 1.0 staging smoke and release evidence

## Control record

- Parent issue: #85
- Work item: #89
- Branch: `sprint1/staging-release-evidence`
- Dependencies: PR #91, PR #92, PR #93, PR #95, and PR #96
- Production baseline: Build 237 at `55afaa689603263c1ad415436e90cce6679808c3`
- Status: Automated disposable-staging gate implemented; shared-host and physical-device evidence pending
- Approval gate: explicit human approval before merge or production cutover

## Automated staging gate

The Release Readiness workflow builds `docker-compose.staging.yml` as a
standalone, disposable stack. It never uses the production Compose file,
production environment file, production database, production volumes, or the
live production URL.

The gate proves:

- frontend health, backend health, and database/storage readiness;
- anonymous denial on protected current `/api/v1` routes;
- administrator login, session identity, read-only core-module access, logout,
  and post-logout denial;
- a staging-only synthetic viewer can read allowed modules but receives `403`
  for user administration and project mutation;
- a project and uploaded document survive an isolated staging backup/restore;
- a project created after the backup disappears after restore, proving the
  rollback boundary rather than only proving that old data remains readable;
- the release evidence bundle is generated from a clean checkout and tied to
  the exact workflow commit.

## Evidence manifest

The generated schema-2 JSON and Markdown evidence records:

- immutable release commit and Git tree;
- SHA-256 checksums for deployment, smoke, recovery, rollback, and operating
  inputs;
- immutable Docker image IDs for backend, frontend, and PostgreSQL;
- the live Alembic revision read from the disposable staging database;
- every required staging gate outcome;
- rollback outcome and `staging_only` scope;
- the protected Build 237 production baseline and `read_only` comparison mode;
- known limitations and pending operator acceptance.

The workflow verifies the artifact before uploading it. The staging profile
fails closed if image IDs, migration revision, rollback proof, required gates,
the exact release SHA, or the protected production baseline are missing.

## Live acceptance still required

The disposable stack is repeatable release-engineering evidence. Sprint 1
cannot be accepted for production until all of the following are separately
recorded:

- approved isolated staging host and DNS name;
- staging-only secrets and OAuth configuration;
- live HTTPS smoke against that host;
- confirmation that the owner-directed voice-control retirement is present in
  the release candidate and no voice UI, runtime, configuration, or gate remains;
- explicit human approval for the dependency PR order, integration merge, and
  any later production cutover.

No production configuration, data, traffic, DNS, or service is changed by this
gate.
