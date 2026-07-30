# Version 1.0 isolated staging environment

## Control record

- Parent issue: #85
- Work item: #90
- Branch: `sprint1/staging-isolation`
- Production baseline: Build 237 at `55afaa689603263c1ad415436e90cce6679808c3`
- Status: Ready for configuration review
- Approval gate: staging host/domain and staging-only credentials before deployment

## Isolation guarantees

The staging stack is standalone and must be operated only through:

```text
scripts/staging-compose.sh
```

The wrapper pins:

- Compose file: `docker-compose.staging.yml`
- Project: `iron-house-os-staging`
- Default env file: `.env.staging`
- Loopback port: `127.0.0.1:8081`

It refuses filenames ending in `production.env`. Do not use `docker-compose.yml`, `docker-compose.production.yml`, `/etc/iron-house-os/production.env`, the production cutover script, the production deploy agent, or the production nginx configuration for staging.

Staging uses its own database name and user, session-cookie name, Docker network, PostgreSQL volume, backend-data volume, release ID, administrator credentials, OAuth URLs, and feature configuration.

## Host preparation

1. Provision or identify a non-production host.
2. Create a staging DNS name and staging-only Google OAuth client.
3. Copy `.env.staging.example` to `.env.staging` on the staging host.
4. Replace every password, secret, release ID, origin, and `staging.invalid` URL.
5. Keep Iron House Chat disabled until an explicit staging API key and test scope are approved.
6. Render the nginx template only after the hostname is final:

   ```text
   envsubst '$IHOS_STAGING_HOST' < ops/digitalocean/nginx-staging.conf.template
   ```

7. Obtain a TLS certificate for the staging hostname before enabling the rendered nginx site.

For the approved single-host DigitalOcean path, use the fail-closed host
operator instead of composing ad hoc commands:

```text
sudo bash ops/digitalocean/staging-deploy.sh \
  --prepare \
  --host staging.os.ironhousecivil.com \
  --release 40_HEX_SHA
```

The operator creates `/etc/iron-house-os/staging.env` and a separate protected
administrator credential file on the host, deploys only the
`iron-house-os-staging` Compose project on loopback port 8081, and runs
authenticated and role-denial smoke checks. It refuses a production environment
file, a dirty or mismatched checkout, and a port already owned by another
workload.

After the DNS A record resolves to the staging host, the operator must obtain
the Let's Encrypt certificate interactively and accept any provider terms
personally. The automated finalizer does not accept certificate terms:

```text
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx gettext-base

sudo certbot certonly \
  --nginx \
  --domain staging.os.ironhousecivil.com \
  --email jeremie@ironhousecontracting.com

sudo bash ops/digitalocean/staging-deploy.sh \
  --finalize-https \
  --host staging.os.ironhousecivil.com \
  --release 40_HEX_SHA
```

Finalization refuses mismatched DNS or a missing certificate, installs only the
staging nginx site, reruns the full HTTPS smoke, and records a secret-free live
acceptance JSON under `/var/lib/iron-house-os/staging/`.

## Validation

Configuration-only validation:

```text
IHOS_STAGING_ENV_FILE=.env.staging.example scripts/staging-compose.sh config --quiet
```

Disposable local gate:

```text
IHOS_STAGING_ENV_FILE=.env.staging.example scripts/staging-compose.sh up -d --build --wait
WEB_URL=http://127.0.0.1:8081 API_URL=http://127.0.0.1:8081 scripts/staging-smoke-test.sh
IHOS_STAGING_ENV_FILE=.env.staging.example scripts/staging-compose.sh down --volumes
```

The example credentials are for configuration and disposable testing only. They are not acceptable for a deployed staging host.

## Deployment blockers

- No staging host or domain has been approved.
- No staging-only secrets or OAuth client have been supplied.
- Physical iPad Safari acceptance is not complete.
- Sprint 1A remains a draft PR and must be integrated before its voice flag can be enabled in a staging image.
