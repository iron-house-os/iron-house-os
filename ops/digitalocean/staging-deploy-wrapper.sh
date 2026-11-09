#!/usr/bin/env bash
set -euo pipefail

release_sha="${1:-}"
app_dir="/opt/iron-house-os-staging-rc-e9cde294"
env_file="/etc/iron-house-os/staging.env"
compose_file="docker-compose.staging.yml"
project_name="iron-house-os-staging"
public_url="https://staging.os.ironhousecivil.com"

[[ "$release_sha" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid release SHA" >&2; exit 2; }

cd "$app_dir"
git fetch --quiet origin main
git merge-base --is-ancestor "$release_sha" origin/main
git checkout --detach "$release_sha"

if ! grep -qE '^OPENAI_API_KEY=.+$' "$env_file"; then
  echo "OPENAI_API_KEY is missing or empty" >&2
  exit 3
fi

docker compose --env-file "$env_file" -f "$compose_file" -p "$project_name" up -d --build --remove-orphans

for attempt in $(seq 1 30); do
  if curl --fail --silent "$public_url/health" >/dev/null; then
    break
  fi
  sleep 5
done

curl --fail --silent --show-error "$public_url/health"
curl --fail --silent --show-error "$public_url/readiness"
docker compose --env-file "$env_file" -f "$compose_file" -p "$project_name" ps

echo "Staging deployment completed for $release_sha"
