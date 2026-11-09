#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
compose_file=${IHOS_COMPOSE_FILE:-docker-compose.production.yml}
compose_env_file=${IHOS_COMPOSE_ENV_FILE:-.env.production}
base_url=${IHOS_BASE_URL:-http://127.0.0.1:${IHOS_PORT:-8080}}
backup=
confirmed=0
skip_safety_backup=0

usage() {
  echo "Usage: scripts/restore.sh --backup DIRECTORY --confirm-restore [--skip-safety-backup]" >&2
}

while (($#)); do
  case "$1" in
    --backup)
      backup=${2:-}
      shift 2
      ;;
    --confirm-restore)
      confirmed=1
      shift
      ;;
    --skip-safety-backup)
      skip_safety_backup=1
      shift
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$backup" || $confirmed -ne 1 ]]; then
  usage
  exit 2
fi
if [[ -z "${BOOTSTRAP_ADMIN_EMAIL:-}" || -z "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
  echo "Export BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD before restoring." >&2
  exit 1
fi

backup=$(cd "$backup" && pwd -P)
cd "$repo_root"
compose=(docker compose --env-file "$compose_env_file" -f "$compose_file")

python scripts/recovery_manifest.py verify --directory "$backup" >/dev/null
"${compose[@]}" config --quiet

if ((skip_safety_backup == 0)); then
  safety_root=${IHOS_SAFETY_BACKUP_ROOT:-$repo_root/backups/pre-restore}
  safety_destination="$safety_root/$(date -u +%Y%m%dT%H%M%SZ)"
  IHOS_COMPOSE_FILE="$compose_file" IHOS_COMPOSE_ENV_FILE="$compose_env_file" \
    scripts/backup.sh --output "$safety_destination"
  echo "Pre-restore safety backup: $safety_destination"
fi

"${compose[@]}" stop frontend backend
"${compose[@]}" up -d --wait postgres
"${compose[@]}" exec -T postgres sh -ceu \
  'dropdb --if-exists --force --maintenance-db=postgres -U "$POSTGRES_USER" "$POSTGRES_DB"; createdb --owner="$POSTGRES_USER" -U "$POSTGRES_USER" "$POSTGRES_DB"'
"${compose[@]}" exec -T postgres sh -ceu \
  'exec pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  <"$backup/database.dump"

"${compose[@]}" run --rm --no-deps -T -v "$backup:/recovery:ro" backend python -c \
  'import pathlib, shutil, tarfile; root=pathlib.Path("/app/data"); root.mkdir(parents=True, exist_ok=True); [shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink() for p in root.iterdir()]; archive=tarfile.open("/recovery/backend-data.tar.gz", "r:gz"); archive.extractall(root, filter="data"); archive.close()'

"${compose[@]}" run --rm --no-deps -T backend alembic upgrade head
"${compose[@]}" up -d --wait
python scripts/release_smoke.py \
  --base-url "$base_url" \
  --email "$BOOTSTRAP_ADMIN_EMAIL" \
  --password "$BOOTSTRAP_ADMIN_PASSWORD" >/dev/null
echo "Recovery restore verified from: $backup"
