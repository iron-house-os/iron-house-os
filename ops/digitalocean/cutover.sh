#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
environment_file=${IHOS_COMPOSE_ENV_FILE:-/etc/iron-house-os/production.env}
export IHOS_COMPOSE_ENV_FILE="$environment_file"
release_sha=
evidence_file=
confirm_go=0
domain=os.ironhousecivil.com

usage() {
  echo "Usage: sudo ops/digitalocean/cutover.sh --release 40_HEX_SHA --evidence evidence.json --confirm-go" >&2
}

while (($#)); do
  case "$1" in
    --release)
      release_sha=${2:-}
      shift 2
      ;;
    --confirm-go)
      confirm_go=1
      shift
      ;;
    --evidence)
      evidence_file=${2:-}
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if ((EUID != 0)) || [[ ! "$release_sha" =~ ^[0-9a-f]{40}$ ]] || [[ ! -f "$evidence_file" ]] || ((confirm_go != 1)); then
  usage
  exit 2
fi
if [[ ! -f /var/lib/iron-house-os/cloud-init-complete ]]; then
  echo "Cloud-init host bootstrap has not completed." >&2
  exit 1
fi
if [[ ! -f "$environment_file" ]]; then
  echo "Missing protected production environment: $environment_file" >&2
  exit 1
fi
evidence_file=$(cd "$(dirname "$evidence_file")" && pwd -P)/$(basename "$evidence_file")
environment_mode=$(stat -c '%a' "$environment_file")
if [[ "$environment_mode" != "600" && "$environment_mode" != "400" ]]; then
  echo "Production environment permissions must be 0600 or 0400." >&2
  exit 1
fi

install_production_business_import_wrapper() {
  local wrapper_source="$repo_root/ops/digitalocean/production-business-import-wrapper.sh"
  local wrapper_target=/usr/local/sbin/ihos-production-business-import
  local sudoers_target=/etc/sudoers.d/iron-house-os-production-business-import
  local sudoers_candidate

  if [[ ! -f "$wrapper_source" ]]; then
    echo "Approved release is missing the production business import wrapper." >&2
    return 1
  fi
  bash -n "$wrapper_source"
  sudoers_candidate=$(mktemp)
  printf '%s\n' \
    "ihos-runner ALL=(root) NOPASSWD: $wrapper_target *" \
    >"$sudoers_candidate"
  chmod 0440 "$sudoers_candidate"
  visudo -cf "$sudoers_candidate" >/dev/null
  install -o root -g root -m 0755 "$wrapper_source" "$wrapper_target"
  install -o root -g root -m 0440 "$sudoers_candidate" "$sudoers_target"
  rm -f "$sudoers_candidate"
  visudo -cf "$sudoers_target" >/dev/null
}


install_production_awarded_invoice_import_wrapper() {
  local wrapper_source="$repo_root/ops/digitalocean/production-awarded-invoice-import-wrapper.sh"
  local wrapper_target=/usr/local/sbin/ihos-production-awarded-invoice-import
  local sudoers_target=/etc/sudoers.d/iron-house-os-production-awarded-invoice-import
  local sudoers_candidate

  if [[ ! -f "$wrapper_source" ]]; then
    echo "Approved release is missing the production awarded-invoice import wrapper." >&2
    return 1
  fi
  bash -n "$wrapper_source"
  sudoers_candidate=$(mktemp)
  printf '%s\n' \
    "ihos-runner ALL=(root) NOPASSWD: $wrapper_target *" \
    >"$sudoers_candidate"
  chmod 0440 "$sudoers_candidate"
  visudo -cf "$sudoers_candidate" >/dev/null
  install -o root -g root -m 0755 "$wrapper_source" "$wrapper_target"
  install -o root -g root -m 0440 "$sudoers_candidate" "$sudoers_target"
  rm -f "$sudoers_candidate"
  visudo -cf "$sudoers_target" >/dev/null
}

cd "$repo_root"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing cutover from a dirty working tree." >&2
  exit 1
fi
git fetch --quiet origin main
git cat-file -e "$release_sha^{commit}"
git checkout --quiet --detach "$release_sha"
if [[ "$(git rev-parse HEAD)" != "$release_sha" ]]; then
  echo "Release checkout identity mismatch." >&2
  exit 1
fi
python scripts/verify_release_candidate_evidence.py \
  --root "$repo_root" \
  --evidence "$evidence_file" \
  --release "$release_sha"

set -a
# shellcheck disable=SC1090
source "$environment_file"
set +a
export IHOS_RELEASE_ID="$release_sha"
: "${BOOTSTRAP_ADMIN_EMAIL:?BOOTSTRAP_ADMIN_EMAIL is required}"
: "${BOOTSTRAP_ADMIN_PASSWORD:?BOOTSTRAP_ADMIN_PASSWORD is required}"
: "${IHOS_STORAGE_BACKEND:?IHOS_STORAGE_BACKEND is required}"
: "${IHOS_STORAGE_S3_BUCKET:?IHOS_STORAGE_S3_BUCKET is required}"
: "${IHOS_BACKUP_S3_BUCKET:?IHOS_BACKUP_S3_BUCKET is required}"
: "${AWS_REGION:?AWS_REGION is required}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}"
: "${IHOS_TLS_EMAIL:?IHOS_TLS_EMAIL is required}"

canonical_email_domain=ironhousecontracting.com
bootstrap_admin_local=${BOOTSTRAP_ADMIN_EMAIL%@*}
bootstrap_admin_domain=${BOOTSTRAP_ADMIN_EMAIL##*@}
if [[ "$BOOTSTRAP_ADMIN_EMAIL" != *@* ||
      -z "$bootstrap_admin_local" ||
      "${bootstrap_admin_domain,,}" != "$canonical_email_domain" ]]; then
  echo "BOOTSTRAP_ADMIN_EMAIL must use the canonical $canonical_email_domain domain before cutover." >&2
  exit 1
fi

if [[ "$IHOS_STORAGE_BACKEND" != "s3" || "$AWS_REGION" != "ca-central-1" ]]; then
  echo "Build 216 requires private S3 storage in ca-central-1." >&2
  exit 1
fi

public_ipv4=$(curl -fsS --max-time 5 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)
dns_ipv4=$(getent ahostsv4 "$domain" | awk 'NR == 1 {print $1}')
if [[ -z "$public_ipv4" || "$dns_ipv4" != "$public_ipv4" ]]; then
  echo "DNS for $domain does not resolve to this Droplet ($public_ipv4)." >&2
  exit 1
fi

scripts/verify_s3_targets.sh "$IHOS_STORAGE_S3_BUCKET" "$IHOS_BACKUP_S3_BUCKET"
compose=(docker compose --env-file "$environment_file" -f docker-compose.production.yml)
"${compose[@]}" config --quiet

recreate_production_stack() {
  local attempt

  for attempt in 1 2; do
    if "${compose[@]}" down --remove-orphans --timeout 30; then
      "${compose[@]}" up -d --no-build --remove-orphans
      return
    fi
    if ((attempt == 1)); then
      echo "Docker Compose cleanup hit transient container state; retrying once." >&2
      sleep 2
    fi
  done

  echo "Docker Compose cleanup failed after two attempts; refusing to recreate production." >&2
  "${compose[@]}" ps --all >&2 || true
  return 1
}

"${compose[@]}" config --format json | python -c '
import json, sys
project = json.load(sys.stdin)
ports = project["services"]["frontend"].get("ports", [])
if not ports or any(port.get("host_ip") != "127.0.0.1" for port in ports):
    raise SystemExit("Frontend must bind only to 127.0.0.1 before cutover.")
'

stamp=$(date -u +%Y%m%dT%H%M%SZ)
IHOS_BACKUP_ROOT=/var/backups/iron-house-os \
IHOS_BACKUP_NAME="pre-cutover-$stamp" \
scripts/scheduled_backup.sh
certbot certonly \
  --webroot \
  --webroot-path /var/www/letsencrypt \
  --domain "$domain" \
  --email "$IHOS_TLS_EMAIL" \
  --agree-tos \
  --non-interactive \
  --keep-until-expiring

gateway_config=/etc/nginx/sites-available/iron-house-os
previous_gateway=$(mktemp)
previous_gateway_present=0
if [[ -f "$gateway_config" ]]; then
  cp --preserve=mode "$gateway_config" "$previous_gateway"
  previous_gateway_present=1
fi
gateway_mutated=0
application_ready=0
rollback_maintenance() {
  status=$?
  if ((status != 0 && gateway_mutated == 1)); then
    if ((application_ready == 1 && previous_gateway_present == 1)); then
      install -m 0644 "$previous_gateway" "$gateway_config"
    else
      install -m 0644 ops/digitalocean/nginx-maintenance.conf "$gateway_config"
    fi
    nginx -t >/dev/null && systemctl reload nginx
  fi
  rm -f "$previous_gateway"
  exit "$status"
}
trap rollback_maintenance EXIT

"${compose[@]}" build
gateway_mutated=1
install -m 0644 ops/digitalocean/nginx-maintenance.conf /etc/nginx/sites-available/iron-house-os
nginx -t
systemctl reload nginx
recreate_production_stack

readiness_url="http://127.0.0.1:${IHOS_PORT:-8080}/readiness"
readiness_file=$(mktemp)
readiness_ready=0
for attempt in $(seq 1 24); do
  if curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
      "$readiness_url" >"$readiness_file" 2>/dev/null &&
    READINESS_FILE="$readiness_file" python -c '
import json, os
with open(os.environ["READINESS_FILE"], encoding="utf-8") as source:
    payload = json.load(source)
release_id = payload.get("checks", {}).get("release_id")
expected = os.environ["IHOS_RELEASE_ID"]
if payload.get("status") != "ready" or release_id != expected:
    raise SystemExit(1)
'; then
    readiness_ready=1
    break
  fi
  echo "Waiting for exact production release readiness (attempt $attempt/24)."
  sleep 5
done
rm -f "$readiness_file"

if ((readiness_ready != 1)); then
  echo "Loopback readiness did not confirm release $IHOS_RELEASE_ID within 120 seconds." >&2
  "${compose[@]}" ps >&2 || true
  exit 1
fi
application_ready=1

install -m 0644 ops/digitalocean/nginx-live.conf "$gateway_config"
nginx -t
systemctl reload nginx
python scripts/release_smoke.py \
  --base-url "https://$domain" \
  --email "$BOOTSTRAP_ADMIN_EMAIL" \
  --password "$BOOTSTRAP_ADMIN_PASSWORD" \
  --full
IHOS_BACKUP_ROOT=/var/backups/iron-house-os \
IHOS_BACKUP_NAME="post-cutover-$stamp" \
IHOS_BACKUP_LOCK_WAIT_SECONDS=300 \
scripts/scheduled_backup.sh
install_production_business_import_wrapper
install_production_awarded_invoice_import_wrapper

acceptance=/var/lib/iron-house-os/operator-acceptance-$stamp.md
cat >"$acceptance" <<EOF
# Iron House OS production operator acceptance

- Release ID: $release_sha
- Commit SHA: $release_sha
- Environment/host: DigitalOcean tor1 / $domain / $public_ipv4
- Cutover window (UTC): $stamp
- Operator: Jeremie Peters
- Operator email: $BOOTSTRAP_ADMIN_EMAIL
- Approver: Jeremie Peters
- Rollback owner: Mac
- Pre-cutover recovery point: s3://$IHOS_BACKUP_S3_BUCKET/${IHOS_BACKUP_S3_PREFIX:-recovery-bundles}/pre-cutover-$stamp.tar.gz
- Release evidence: $evidence_file
- Observed health/readiness: passed
- Authenticated smoke result: passed
- Document upload/download result: passed by full local smoke
- TLS result: passed
- Post-cutover recovery point: s3://$IHOS_BACKUP_S3_BUCKET/${IHOS_BACKUP_S3_PREFIX:-recovery-bundles}/post-cutover-$stamp.tar.gz
- Decision: GO
- Decision time (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
chmod 0600 "$acceptance"
rm -f "$previous_gateway"
trap - EXIT
echo "Release $release_sha live cutover passed: https://$domain"
echo "Operator acceptance: $acceptance"

