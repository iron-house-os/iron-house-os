# Iron House OS release runbook

Build 207 packages IHOS as a single-node production stack. Build 208 adds database-backed user accounts and signed HTTP-only sessions. Build 209 makes Alembic the schema authority and adds database-plus-upload recovery bundles with an automated restore drill. Nginx serves the compiled responsive web app and proxies `/api/v1` to FastAPI; FastAPI protects business routes, applies migrations, creates the first administrator once, and stores uploads and audit events on a persistent volume. PostgreSQL uses a separate persistent volume.

## Host requirements

- A Docker host with Docker Compose v2
- A DNS name pointed at the host
- An HTTPS reverse proxy or managed load balancer in front of port 8080
- Scheduled, off-host storage for recovery bundles created by `scripts/backup.sh`

Do not expose the Compose port directly to the public internet. HTTPS must be terminated upstream so credentials, session cookies, and project data are encrypted in transit.

## First deployment

1. Create the environment file and replace every placeholder.

```bash
cp .env.production.example .env.production
openssl rand -hex 32
```

Use generated values for the database password, application secret, and bootstrap administrator password. Keep `.env.production` out of source control. Leave `SESSION_COOKIE_SECURE=true` for every HTTPS deployment.

2. Validate the fully rendered Compose configuration.

```bash
docker compose --env-file .env.production -f docker-compose.production.yml config --quiet
```

3. Build and start the stack. The backend applies Alembic, creates the bootstrap administrator only when its email does not already exist, and then starts Uvicorn. A partial unversioned schema fails migration instead of being changed implicitly.

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build --wait
```

4. Run the read-only release check first. An HTTP loopback check requires `SESSION_COOKIE_SECURE=false` and must only be used while port 8080 is firewalled or bound to localhost. Restore `SESSION_COOKIE_SECURE=true` before public HTTPS access.

```bash
set -a
source .env.production
set +a
python scripts/release_smoke.py --base-url http://127.0.0.1:8080
```

5. Run the full project-to-drawing smoke path. This creates a project, calculates a one-line estimate, creates an RFQ package, and uploads a small civil PDF.

```bash
python scripts/release_smoke.py --base-url http://127.0.0.1:8080 --full
```

6. Point the HTTPS proxy at the host and repeat the read-only check against the public staging URL.

```bash
python scripts/release_smoke.py --base-url https://your-staging-host.example
```

The public URL can then be shared from a phone or desktop browser as a QR code. Each person should receive an individual user account; do not share the bootstrap administrator password.

## User access

- Sign in with the bootstrap administrator email and password from `.env.production`.
- Administrators can create, update, deactivate, and reset accounts through `/api/v1/users`.
- Roles are `admin`, `operations_manager`, `estimator`, and `viewer`.
- Viewers are read-only. Estimators can mutate estimating, procurement, project, document, tender, and bid workflows but not fleet data or users. Operations managers can mutate all business modules. Only administrators can manage user accounts.
- Denied module actions are written to the durable audit stream without request bodies, credentials, or session tokens.
- Role changes, deactivation, and password resets invalidate that user's existing sessions.
- Remove `BOOTSTRAP_ADMIN_PASSWORD` from routine operator notes after the first successful start. The startup task never overwrites an existing account password.

## Operations

Inspect service health and logs:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml ps
docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=200
```

Deploy a new revision without removing persistent data:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build --wait
```

Stop services without deleting data:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml down
```

Never add `--volumes` to the production shutdown command unless a verified restore is available and data deletion is intentional.

## Backup

Create a consistent recovery bundle during a short maintenance window. The script pauses the application services, dumps PostgreSQL, archives `/app/data`, writes SHA-256 checksums and the Alembic revision, then restarts the stack. It refuses to overwrite an existing destination and never copies the environment file.

```bash
set -a
source .env.production
set +a
scripts/backup.sh --output "/secure/off-host/ihos-$(date -u +%Y%m%dT%H%M%SZ)"
```

Copy completed bundles off the Docker host. Keep `.env.production` and its secret-key recovery procedure in a separate protected secret store; neither belongs in the data bundle.

## Restore

Restore is intentionally destructive and requires an explicit confirmation flag. By default it creates a timestamped safety backup under `backups/pre-restore`, verifies the requested bundle checksums before changing data, recreates the database, restores uploads and audit data, applies any newer migrations, starts the stack, and runs the authenticated read-only release check.

```bash
set -a
source .env.production
set +a
scripts/restore.sh \
  --backup /secure/off-host/ihos-20260714T120000Z \
  --confirm-restore
```

`--skip-safety-backup` is reserved for disposable CI restore drills. After a production restore, run the full smoke path and inspect a known project and document:

```bash
python scripts/release_smoke.py --base-url https://your-production-host.example --full
```

The release-readiness workflow performs the same backup and restore against a disposable production stack, then proves that a sentinel database record and its uploaded PDF survived with the same checksum.

## Known limitations

- Build 207 does not provision a cloud account, domain, certificate, or paid infrastructure.
- User roles currently control account administration and document-audit access; fine-grained permissions for every business module remain future work.
- Login throttling, password recovery email, and multi-factor authentication are not yet implemented.
- Local Docker volumes remain single-node storage; scheduling and off-host retention of recovery bundles are operator responsibilities.
- Gmail and Drive remain preview-only and perform no external actions.
