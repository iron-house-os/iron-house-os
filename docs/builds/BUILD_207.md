# Build 207 — working web-app release

## Outcome

IHOS can now run as a production-shaped single-node web application behind one URL. The release stack compiles the frontend, proxies browser API traffic through the same origin, migrates the database before startup, persists uploads and audit events, and blocks access with a browser login.

## Status

- Production Compose, Nginx login gate, same-origin API routing, PostgreSQL, uploads, audit persistence, and readiness probes are implemented.
- GitHub release validation boots the actual production stack and tests project creation, estimate calculation, RFQ creation, and civil PDF upload.
- Cloud infrastructure is intentionally not provisioned because the repository has no selected host, domain, credentials, or approved spend.

## Risks

- A single shared browser credential is only a staging access gate; per-user identity and authorization remain unfinished.
- Docker volumes need host-level backups and a restore drill before production data is entrusted to the stack.
- Public access requires an HTTPS ingress, DNS, and a hosting decision outside this code change.

## Exact first deployment step

Copy `.env.production.example` to `.env.production`, replace every placeholder with generated secrets, then run `docker compose --env-file .env.production -f docker-compose.production.yml up -d --build --wait` on the chosen staging Docker host.
