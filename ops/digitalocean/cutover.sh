#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
environment_file=${IHOS_COMPOSE_ENV_FILE:-/etc/iron-house-os/production.env}
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
"${compose[@]}" config --format json | python -c '
import json, sys
project = json.load(sys.stdin)
ports = project["services"]["frontend"].get("ports", [])
if not ports or any(port.get("host_ip") != "127.0.0.1" for port in ports):
    raise SystemExit("Frontend must bind only to 127.0.0.1 before cutover.")
'

install -m 0644 ops/digitalocean/nginx-maintenance.conf /etc/nginx/sites-available/iron-house-os
nginx -t
systemctl reload nginx
"${compose[@]}" up -d --build --wait
curl -fsS "http://127.0.0.1:${IHOS_PORT:-8080}/readiness" | python -c '
import json, sys
payload = json.load(sys.stdin)
if payload.get("status") != "ready":
    raise SystemExit(f"Loopback readiness failed: {payload}")
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

live_enabled=0
rollback_maintenance() {
  status=$?
  if ((status != 0 && live_enabled == 1)); then
    install -m 0644 ops/digitalocean/nginx-maintenance.conf /etc/nginx/sites-available/iron-house-os
    nginx -t >/dev/null && systemctl reload nginx
  fi
  exit "$status"
}
trap rollback_maintenance EXIT
install -m 0644 ops/digitalocean/nginx-live.conf /etc/nginx/sites-available/iron-house-os
nginx -t
systemctl reload nginx
live_enabled=1
python scripts/release_smoke.py \
  --base-url "https://$domain" \
  --email "$BOOTSTRAP_ADMIN_EMAIL" \
  --password "$BOOTSTRAP_ADMIN_PASSWORD" \
  --full
IHOS_BACKUP_ROOT=/var/backups/iron-house-os \
IHOS_BACKUP_NAME="post-cutover-$stamp" \
scripts/scheduled_backup.sh

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
live_enabled=0
trap - EXIT
echo "Release $release_sha live cutover passed: https://$domain"
echo "Operator acceptance: $acceptance"
