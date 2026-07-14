# Iron House OS release runbook

Build 207 packages IHOS as a single-node production stack. Nginx serves the compiled responsive web app, protects it with a temporary browser login, and proxies `/api/v1` to FastAPI. FastAPI runs migrations before accepting traffic and stores uploads and audit events on a persistent volume. PostgreSQL uses a separate persistent volume.

## Host requirements

- A Docker host with Docker Compose v2
- A DNS name pointed at the host
- An HTTPS reverse proxy or managed load balancer in front of port 8080
- Automated backups for the `postgres_data` and `backend_data` volumes

Do not expose the Compose port directly to the public internet. The built-in login gate is suitable for controlled staging access, but HTTPS must be terminated upstream so credentials and project data are encrypted in transit.

## First deployment

1. Create the environment file and replace every placeholder.

```bash
cp .env.production.example .env.production
openssl rand -hex 32
```

Use generated values for the database password, application secret, and browser login password. Keep `.env.production` out of source control.

2. Validate the fully rendered Compose configuration.

```bash
docker compose --env-file .env.production -f docker-compose.production.yml config --quiet
```

3. Build and start the stack. The backend applies Alembic migrations before Uvicorn starts.

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build --wait
```

4. Run the read-only release check first.

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

The public URL can then be shared from a phone or desktop browser as a QR code. Credentials must be shared separately and rotated when staging access changes.

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

## Known limitations

- Build 207 does not provision a cloud account, domain, certificate, or paid infrastructure.
- The temporary Nginx browser login is one shared credential, not per-user authorization or an audit identity.
- Local Docker volumes are single-node storage; object storage, replication, and automated restore drills remain future release work.
- Gmail and Drive remain preview-only and perform no external actions.
