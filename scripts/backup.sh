#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
compose_file=${IHOS_COMPOSE_FILE:-docker-compose.production.yml}
compose_env_file=${IHOS_COMPOSE_ENV_FILE:-.env.production}
output=

usage() {
  echo "Usage: scripts/backup.sh --output DIRECTORY" >&2
}

while (($#)); do
  case "$1" in
    --output)
      output=${2:-}
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$output" ]]; then
  usage
  exit 2
fi

mkdir -p "$(dirname "$output")"
output_parent=$(cd "$(dirname "$output")" && pwd -P)
output="$output_parent/$(basename "$output")"
if [[ -e "$output" ]]; then
  echo "Backup destination already exists: $output" >&2
  exit 1
fi

cd "$repo_root"
compose=(docker compose --env-file "$compose_env_file" -f "$compose_file")
temporary=$(mktemp -d "${output}.tmp.XXXXXX")
services_stopped=0

cleanup() {
  status=$?
  if ((services_stopped)); then
    "${compose[@]}" up -d --wait >/dev/null || true
  fi
  if ((status != 0)); then
    rm -rf "$temporary"
  fi
  exit "$status"
}
trap cleanup EXIT

"${compose[@]}" config --quiet
"${compose[@]}" up -d --wait postgres
"${compose[@]}" stop frontend backend
services_stopped=1

schema_revision=$(
  "${compose[@]}" exec -T postgres sh -ceu \
    'exec psql -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version_num FROM alembic_version"'
)
if [[ -z "$schema_revision" || "$schema_revision" == *$'\n'* ]]; then
  echo "Database has no single Alembic schema revision." >&2
  exit 1
fi

"${compose[@]}" exec -T postgres sh -ceu \
  'exec pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  >"$temporary/database.dump"

"${compose[@]}" run --rm --no-deps -T backend python -c \
  'import sys, tarfile; archive=tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"); archive.add("/app/data", arcname="."); archive.close()' \
  >"$temporary/backend-data.tar.gz"

python scripts/recovery_manifest.py create \
  --directory "$temporary" \
  --schema-revision "$schema_revision" >/dev/null

"${compose[@]}" up -d --wait
services_stopped=0
mv "$temporary" "$output"
trap - EXIT
echo "Recovery backup created: $output"
