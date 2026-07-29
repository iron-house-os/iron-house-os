#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$root_dir/docker-compose.staging.yml"
env_file="${IHOS_STAGING_ENV_FILE:-$root_dir/.env.staging}"
project_name="iron-house-os-staging"
docker_bin="$(command -v docker || true)"

if [[ -z "$docker_bin" || ! -x "$docker_bin" ]]; then
  echo "Docker CLI is required to operate the staging stack." >&2
  exit 1
fi

if [[ "$env_file" == *production.env || "$env_file" == *.production.env ]]; then
  echo "Refusing to use a production environment file for staging." >&2
  exit 1
fi

if [[ ! -f "$env_file" ]]; then
  echo "Missing staging environment file: $env_file" >&2
  echo "Copy .env.staging.example to .env.staging and replace every placeholder." >&2
  exit 1
fi

exec "$docker_bin" compose \
  --project-name "$project_name" \
  --env-file "$env_file" \
  -f "$compose_file" \
  "$@"
