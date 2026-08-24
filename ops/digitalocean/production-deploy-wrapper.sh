#!/usr/bin/env bash
set -euo pipefail

release_sha=
evidence_file=

usage() {
  echo "Usage: ihos-production-deploy --release 40_HEX_SHA --evidence evidence.json" >&2
}

while (($#)); do
  case "$1" in
    --release)
      release_sha=${2:-}
      shift 2
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

if ((EUID != 0)) || [[ ! "$release_sha" =~ ^[0-9a-f]{40}$ ]] || [[ ! -f "$evidence_file" ]]; then
  usage
  exit 2
fi

if [[ "$(hostname)" != "iron-house-os-prod-1" ]]; then
  echo "Refusing production deployment on unexpected host." >&2
  exit 1
fi

workflow_root=$(pwd -P)
git_workflow() {
  git -c "safe.directory=$workflow_root" -C "$workflow_root" "$@"
}

resolved_workflow_root=$(git_workflow rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "$resolved_workflow_root" || "$(cd "$resolved_workflow_root" && pwd -P)" != "$workflow_root" ]]; then
  echo "Current directory is not an Iron House OS checkout." >&2
  exit 1
fi

evidence_file=$(cd "$(dirname "$evidence_file")" && pwd -P)/$(basename "$evidence_file")
remote_url=$(git_workflow remote get-url origin)

case "$remote_url" in
  https://github.com/iron-house-os/iron-house-os|https://github.com/iron-house-os/iron-house-os.git|git@github.com:iron-house-os/iron-house-os.git)
    ;;
  *)
    echo "Unexpected repository remote: $remote_url" >&2
    exit 1
    ;;
esac

if [[ "$(git_workflow rev-parse HEAD)" != "$release_sha" ]]; then
  echo "Checked-out release does not match the approved SHA." >&2
  exit 1
fi
if [[ -n "$(git_workflow status --porcelain)" ]]; then
  echo "Refusing deployment from a dirty release checkout." >&2
  exit 1
fi

git_workflow fetch --quiet origin main
if ! git_workflow merge-base --is-ancestor "$release_sha" origin/main; then
  echo "Approved release is not present on origin/main." >&2
  exit 1
fi

production_projects() {
  local include_stopped=${1:-0}
  local -a docker_ps=(docker ps)
  if ((include_stopped == 1)); then
    docker_ps+=(--all)
  fi
  docker_ps+=(--filter label=com.docker.compose.service=frontend --format '{{.ID}}')

  while IFS= read -r container_id; do
    config_files=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$container_id")
    if [[ "$config_files" == *docker-compose.production.yml* ]]; then
      docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$container_id"
    fi
  done < <("${docker_ps[@]}")
}

mapfile -t production_candidates < <(production_projects 0 | sed '/^$/d' | sort -u)
if (("${#production_candidates[@]}" == 0)); then
  mapfile -t production_candidates < <(production_projects 1 | sed '/^$/d' | sort -u)
  if (("${#production_candidates[@]}" == 1)); then
    echo "Recovering stopped production Compose project: ${production_candidates[0]}"
  fi
fi

if (("${#production_candidates[@]}" != 1)); then
  echo "Exactly one production Compose project is required; found ${#production_candidates[@]}." >&2
  exit 1
fi
production_project=${production_candidates[0]}

release_root="/opt/iron-house-os-releases/$release_sha"
if [[ ! -d "$release_root/.git" ]]; then
  install -d -o root -g root -m 0750 "$(dirname "$release_root")"
  git -c "safe.directory=$workflow_root" clone --quiet --no-checkout --no-local --no-hardlinks "$workflow_root" "$release_root"
  git -C "$release_root" remote set-url origin https://github.com/iron-house-os/iron-house-os.git
  git -C "$release_root" checkout --quiet --detach "$release_sha"
fi

if [[ "$(git -C "$release_root" rev-parse HEAD)" != "$release_sha" ]] || [[ -n "$(git -C "$release_root" status --porcelain)" ]]; then
  echo "Immutable production release checkout is missing, dirty, or has the wrong SHA." >&2
  exit 1
fi
if [[ ! -f "$release_root/ops/digitalocean/cutover.sh" ]]; then
  echo "Approved release does not contain the guarded cutover script." >&2
  exit 1
fi

export COMPOSE_PROJECT_NAME="$production_project"
cd "$release_root"
exec /bin/bash "$release_root/ops/digitalocean/cutover.sh" \
  --release "$release_sha" \
  --evidence "$evidence_file" \
  --confirm-go
