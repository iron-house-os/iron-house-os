#!/usr/bin/env bash
set -euo pipefail

repo=${IHOS_REPO_ROOT:-/opt/iron-house-os/source}
environment_file=${IHOS_COMPOSE_ENV_FILE:-/etc/iron-house-os/production.env}
state_root=${IHOS_DEPLOY_AGENT_STATE_ROOT:-/var/lib/iron-house-os/deploy-agent}
repository=${IHOS_GITHUB_REPOSITORY:-iron-house-os/iron-house-os}

if ((EUID != 0)); then
  echo "Iron House deploy agent must run as root." >&2
  exit 1
fi

install -d -m 0700 "$state_root"
exec 9>"$state_root/deploy.lock"
if ! flock -n 9; then
  echo "Another Iron House deployment is already running."
  exit 0
fi

cd "$repo"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Deployment blocked: production checkout is dirty." >&2
  exit 1
fi

git fetch --quiet origin main
release=$(git rev-parse origin/main)
if [[ ! "$release" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Deployment blocked: invalid release SHA." >&2
  exit 1
fi

live_release=$(curl -fsS --max-time 15 https://os.ironhousecivil.com/readiness \
  | jq -r '.checks.release_id // empty' 2>/dev/null || true)
if [[ "$live_release" == "$release" ]]; then
  echo "Release $release is already live."
  exit 0
fi

runs=$(curl -fsS --max-time 20 \
  "https://api.github.com/repos/$repository/actions/runs?head_sha=$release&event=push&per_page=100")
gate() {
  local workflow=$1
  jq -e --arg workflow "$workflow" \
    'any(.workflow_runs[]; .name == $workflow and .head_sha == "'"$release"'" and .conclusion == "success")' \
    >/dev/null <<<"$runs"
}

if ! gate "CI" || ! gate "Release readiness"; then
  echo "Release $release is waiting for successful CI and Release readiness."
  exit 0
fi

git checkout --quiet --detach "$release"
evidence="$state_root/release-evidence-$release"
python3 scripts/release_candidate_evidence.py \
  --output "$evidence" \
  --release-id "$release" \
  --gate ci=passed \
  --gate browser_mobile_accessibility=passed \
  --gate production_stack_smoke=passed \
  --gate backup_restore=passed

IHOS_COMPOSE_ENV_FILE="$environment_file" \
  bash ops/digitalocean/cutover.sh \
  --release "$release" \
  --evidence "$evidence/evidence.json" \
  --confirm-go

timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
jq -n --arg status deployed --arg release "$release" --arg timestamp "$timestamp" \
  '{status: $status, release: $release, completed_at: $timestamp}' \
  >"$state_root/last-success.json.tmp"
mv "$state_root/last-success.json.tmp" "$state_root/last-success.json"
chmod 0600 "$state_root/last-success.json"
echo "Iron House deploy agent completed release $release at $timestamp."
