#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
environment_file=${IHOS_STAGING_ENV_FILE:-/etc/iron-house-os/staging.env}
credentials_file=${IHOS_STAGING_CREDENTIALS_FILE:-/etc/iron-house-os/staging-admin-credentials}
state_root=${IHOS_STAGING_STATE_ROOT:-/var/lib/iron-house-os/staging}
nginx_site=/etc/nginx/sites-available/iron-house-os-staging
nginx_enabled=/etc/nginx/sites-enabled/iron-house-os-staging
production_baseline=55afaa689603263c1ad415436e90cce6679808c3
staging_host=
release_sha=
mode=

usage() {
  cat >&2 <<'EOF'
Usage:
  sudo bash ops/digitalocean/staging-deploy.sh \
    --prepare \
    --host staging.os.ironhousecivil.com \
    --release 40_HEX_SHA

  sudo bash ops/digitalocean/staging-deploy.sh \
    --finalize-https \
    --host staging.os.ironhousecivil.com \
    --release 40_HEX_SHA
EOF
}

while (($#)); do
  case "$1" in
    --prepare|--finalize-https)
      if [[ -n "$mode" ]]; then
        usage
        exit 2
      fi
      mode=${1#--}
      shift
      ;;
    --host)
      staging_host=${2:-}
      shift 2
      ;;
    --release)
      release_sha=${2:-}
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if ((EUID != 0)) ||
  [[ -z "$mode" ]] ||
  [[ "$staging_host" != "staging.os.ironhousecivil.com" ]] ||
  [[ ! "$release_sha" =~ ^[0-9a-f]{40}$ ]]; then
  usage
  exit 2
fi

if [[ "$environment_file" == *production.env ||
  "$environment_file" == *.production.env ||
  "$environment_file" == "/etc/iron-house-os/production.env" ]]; then
  echo "Refusing to use a production environment file for staging." >&2
  exit 1
fi

for command in curl docker flock git openssl python3 stat; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing required host command: $command" >&2
    exit 1
  fi
done
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required." >&2
  exit 1
fi

cd "$repo_root"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Deployment blocked: staging checkout is dirty." >&2
  exit 1
fi
if [[ "$(git rev-parse HEAD)" != "$release_sha" ]]; then
  echo "Deployment blocked: checkout does not match release $release_sha." >&2
  exit 1
fi

install -d -m 0700 /etc/iron-house-os "$state_root"
exec 9>"$state_root/deploy.lock"
if ! flock -n 9; then
  echo "Another staging deployment is already running." >&2
  exit 1
fi

write_staging_environment() {
  if [[ -e "$environment_file" || -e "$credentials_file" ]]; then
    if [[ ! -f "$environment_file" || ! -f "$credentials_file" ]]; then
      echo "Incomplete existing staging credentials; refusing to overwrite." >&2
      exit 1
    fi
    return
  fi

  umask 077
  local postgres_password secret_key admin_password
  postgres_password=$(openssl rand -hex 32)
  secret_key=$(openssl rand -hex 48)
  admin_password=$(openssl rand -hex 32)

  {
    echo "POSTGRES_DB=iron_house_os_staging"
    echo "POSTGRES_USER=iron_house_staging"
    echo "POSTGRES_PASSWORD=$postgres_password"
    echo "SECRET_KEY=$secret_key"
    echo "BOOTSTRAP_ADMIN_EMAIL=staging-admin@ironhousecontracting.com"
    echo "BOOTSTRAP_ADMIN_PASSWORD=$admin_password"
    echo "BOOTSTRAP_ADMIN_NAME=Iron House Staging Administrator"
    echo "SESSION_COOKIE_NAME=ihos_staging_session"
    echo "SESSION_COOKIE_SECURE=true"
    echo "LOGIN_MAX_FAILED_ATTEMPTS=5"
    echo "LOGIN_LOCKOUT_MINUTES=15"
    echo "BACKEND_CORS_ORIGINS='[\"https://$staging_host\"]'"
    echo "IHOS_STORAGE_BACKEND=local"
    echo "IHOS_STORAGE_ROOT=/app/data/uploads"
    echo "IHOS_STORAGE_CACHE_ROOT=/app/data/object-cache"
    echo "OPENAI_API_KEY="
    echo "OPENAI_CHAT_MODEL=gpt-5.6-sol"
    echo "OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe"
    echo "IRON_HOUSE_CHAT_ENABLED=false"
    echo "MEETING_MINUTES_ENABLED=true"
    echo "GOOGLE_CALENDAR_ENABLED=false"
    echo "GOOGLE_CALENDAR_CLIENT_ID="
    echo "GOOGLE_CALENDAR_CLIENT_SECRET="
    echo "GOOGLE_CALENDAR_REDIRECT_URI=https://$staging_host/api/v1/google-calendar/oauth/callback"
    echo "GOOGLE_CALENDAR_FRONTEND_RETURN_URL=https://$staging_host/google-calendar"
    echo "GOOGLE_CALENDAR_TOKEN_ENCRYPTION_KEY="
    echo "IHOS_STAGING_RELEASE_ID=$release_sha"
    echo "IHOS_STAGING_PORT=8081"
    echo "VITE_HEY_CHAT_VOICE_ENABLED=true"
    echo "VITE_PERFORMANCE_OBSERVABILITY_ENABLED=true"
  } >"$environment_file"

  {
    echo "STAGING_EMAIL=staging-admin@ironhousecontracting.com"
    echo "STAGING_PASSWORD=$admin_password"
  } >"$credentials_file"
  chmod 0600 "$environment_file" "$credentials_file"
}

load_staging_credentials() {
  if [[ ! -f "$environment_file" || ! -f "$credentials_file" ]]; then
    echo "Missing protected staging environment or administrator credentials." >&2
    exit 1
  fi
  if [[ "$(stat -c '%a' "$environment_file")" != "600" ||
    "$(stat -c '%a' "$credentials_file")" != "600" ]]; then
    echo "Staging secret files must be mode 0600." >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$environment_file"
  # shellcheck disable=SC1090
  source "$credentials_file"
  set +a
  if [[ "$IHOS_STAGING_RELEASE_ID" != "$release_sha" ]]; then
    echo "Existing staging environment targets a different release." >&2
    exit 1
  fi
}

run_smoke() {
  local url=$1
  WEB_URL="$url" \
    API_URL="$url" \
    STAGING_EMAIL="$STAGING_EMAIL" \
    STAGING_PASSWORD="$STAGING_PASSWORD" \
    STAGING_SYNTHETIC_DATA=true \
    STAGING_SYNTHETIC_SUFFIX="live-${release_sha:0:12}-$(date +%s)-$$" \
    scripts/staging-smoke-test.sh
}

record_acceptance() {
  local public_url=$1
  local backend_image frontend_image postgres_image alembic_revision output
  backend_image=$(IHOS_STAGING_ENV_FILE="$environment_file" scripts/staging-compose.sh images -q backend)
  frontend_image=$(IHOS_STAGING_ENV_FILE="$environment_file" scripts/staging-compose.sh images -q frontend)
  postgres_image=$(IHOS_STAGING_ENV_FILE="$environment_file" scripts/staging-compose.sh images -q postgres)
  alembic_revision=$(
    IHOS_STAGING_ENV_FILE="$environment_file" \
      scripts/staging-compose.sh exec -T postgres sh -ceu \
      'psql -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version_num FROM alembic_version"'
  )
  output="$state_root/live-acceptance-${release_sha:0:12}.json"
  ACCEPTANCE_OUTPUT="$output" \
    ACCEPTANCE_RELEASE="$release_sha" \
    ACCEPTANCE_BASELINE="$production_baseline" \
    ACCEPTANCE_URL="$public_url" \
    ACCEPTANCE_BACKEND_IMAGE="$backend_image" \
    ACCEPTANCE_FRONTEND_IMAGE="$frontend_image" \
    ACCEPTANCE_POSTGRES_IMAGE="$postgres_image" \
    ACCEPTANCE_ALEMBIC="$alembic_revision" \
    python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

payload = {
    "environment": "staging",
    "release": os.environ["ACCEPTANCE_RELEASE"],
    "production_baseline": os.environ["ACCEPTANCE_BASELINE"],
    "production_comparison": "read_only",
    "url": os.environ["ACCEPTANCE_URL"],
    "images": {
        "backend": os.environ["ACCEPTANCE_BACKEND_IMAGE"],
        "frontend": os.environ["ACCEPTANCE_FRONTEND_IMAGE"],
        "postgres": os.environ["ACCEPTANCE_POSTGRES_IMAGE"],
    },
    "alembic_revision": os.environ["ACCEPTANCE_ALEMBIC"],
    "live_https_smoke": "passed",
    "authenticated_smoke": "passed",
    "role_denial": "passed",
    "synthetic_data": "passed",
    "physical_ipad_safari": "pending",
    "recorded_at": datetime.now(timezone.utc).isoformat(),
}
output = Path(os.environ["ACCEPTANCE_OUTPUT"])
output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
output.chmod(0o600)
PY
  echo "Live staging acceptance recorded at $output"
}

if [[ "$mode" == "prepare" ]]; then
  if [[ -n "$(docker ps -q --filter label=com.docker.compose.project=iron-house-os-staging)" ]]; then
    echo "Existing IHOS staging containers found; performing an idempotent update."
  elif command -v ss >/dev/null 2>&1 && ss -H -ltn | awk '{print $4}' | grep -Eq '(^|:)8081$'; then
    echo "Port 8081 is already in use by a non-staging workload." >&2
    exit 1
  fi

  write_staging_environment
  load_staging_credentials
  IHOS_STAGING_ENV_FILE="$environment_file" scripts/staging-compose.sh config --quiet
  IHOS_STAGING_ENV_FILE="$environment_file" scripts/staging-compose.sh up -d --build --wait
  run_smoke "http://127.0.0.1:8081"
  echo "Staging stack prepared on loopback port 8081."
  echo "Protected administrator credentials: $credentials_file"
  echo "Next: create the DNS A record, obtain the TLS certificate interactively, then run --finalize-https."
  exit 0
fi

for command in envsubst nginx; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing required HTTPS command: $command" >&2
    exit 1
  fi
done
load_staging_credentials

public_ipv4=$(curl -fsS --max-time 5 \
  http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)
dns_ipv4=$(getent ahostsv4 "$staging_host" | awk 'NR == 1 {print $1}')
if [[ -z "$public_ipv4" || "$dns_ipv4" != "$public_ipv4" ]]; then
  echo "DNS for $staging_host does not resolve to this staging host ($public_ipv4)." >&2
  exit 1
fi
if [[ ! -s "/etc/letsencrypt/live/$staging_host/fullchain.pem" ||
  ! -s "/etc/letsencrypt/live/$staging_host/privkey.pem" ]]; then
  echo "TLS certificate is missing." >&2
  echo "Obtain it interactively before finalization:" >&2
  echo "  certbot certonly --nginx --domain $staging_host --email jeremie@ironhousecontracting.com" >&2
  exit 1
fi

IHOS_STAGING_HOST="$staging_host" \
  envsubst '$IHOS_STAGING_HOST' \
  <ops/digitalocean/nginx-staging.conf.template \
  >"$nginx_site.tmp"
install -m 0644 "$nginx_site.tmp" "$nginx_site"
rm -f "$nginx_site.tmp"
ln -sfn "$nginx_site" "$nginx_enabled"
nginx -t
systemctl reload nginx
run_smoke "https://$staging_host"
record_acceptance "https://$staging_host"
echo "Live staging deployment passed: https://$staging_host"
