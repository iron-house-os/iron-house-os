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

repo_root=$(git -C "$(pwd -P)" rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "$repo_root" || ! -f "$repo_root/ops/digitalocean/cutover.sh" ]]; then
  echo "Current directory is not an Iron House OS checkout." >&2
  exit 1
fi

repo_root=$(cd "$repo_root" && pwd -P)
evidence_file=$(cd "$(dirname "$evidence_file")" && pwd -P)/$(basename "$evidence_file")
remote_url=$(git -C "$repo_root" remote get-url origin)

case "$remote_url" in
  https://github.com/iron-house-os/iron-house-os|https://github.com/iron-house-os/iron-house-os.git|git@github.com:iron-house-os/iron-house-os.git)
    ;;
  *)
    echo "Unexpected repository remote: $remote_url" >&2
    exit 1
    ;;
esac

if [[ "$(git -C "$repo_root" rev-parse HEAD)" != "$release_sha" ]]; then
  echo "Checked-out release does not match the approved SHA." >&2
  exit 1
fi
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "Refusing deployment from a dirty release checkout." >&2
  exit 1
fi

git -C "$repo_root" fetch --quiet origin main
if ! git -C "$repo_root" merge-base --is-ancestor "$release_sha" origin/main; then
  echo "Approved release is not present on origin/main." >&2
  exit 1
fi

exec "$repo_root/ops/digitalocean/cutover.sh" \
  --release "$release_sha" \
  --evidence "$evidence_file" \
  --confirm-go
