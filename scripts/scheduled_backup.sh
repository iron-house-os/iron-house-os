#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
backup_root=${IHOS_BACKUP_ROOT:-$repo_root/backups/scheduled}
backup_name=${IHOS_BACKUP_NAME:-$(date -u +%Y%m%dT%H%M%SZ)}
retention_days=${IHOS_BACKUP_RETENTION_DAYS:-30}
keep_minimum=${IHOS_BACKUP_KEEP_MINIMUM:-7}
maximum_bundles=${IHOS_BACKUP_MAXIMUM_BUNDLES:-60}
backup_lock_wait_seconds=${IHOS_BACKUP_LOCK_WAIT_SECONDS:-0}

if [[ ! "$backup_lock_wait_seconds" =~ ^[0-9]+$ ]] ||
  ((10#$backup_lock_wait_seconds > 600)); then
  echo "IHOS_BACKUP_LOCK_WAIT_SECONDS must be an integer from 0 to 600." >&2
  exit 2
fi

if [[ ! "$backup_name" =~ ^[A-Za-z0-9._-]+$ ]] || [[ "$backup_name" == "." || "$backup_name" == ".." ]]; then
  echo "IHOS_BACKUP_NAME must be a safe single directory name." >&2
  exit 2
fi

mkdir -p "$backup_root"
backup_root=$(cd "$backup_root" && pwd -P)
exec 9>"$backup_root/.backup.lock"
if ! flock --wait "$backup_lock_wait_seconds" 9; then
  echo "Another Iron House OS backup is already running after waiting ${backup_lock_wait_seconds}s." >&2
  exit 1
fi

cd "$repo_root"
backup_path="$backup_root/$backup_name"
scripts/backup.sh --output "$backup_path"
if [[ -n "${IHOS_BACKUP_S3_BUCKET:-}" ]]; then
  scripts/upload_backup_s3.sh \
    --backup "$backup_path" \
    --bucket "$IHOS_BACKUP_S3_BUCKET" \
    --prefix "${IHOS_BACKUP_S3_PREFIX:-recovery-bundles}"
fi
python scripts/backup_retention.py \
  --root "$backup_root" \
  --retention-days "$retention_days" \
  --keep-minimum "$keep_minimum" \
  --maximum-bundles "$maximum_bundles" \
  --apply
