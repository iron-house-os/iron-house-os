#!/usr/bin/env bash
set -euo pipefail

backup=
bucket=
prefix=recovery-bundles

usage() {
  echo "Usage: scripts/upload_backup_s3.sh --backup DIRECTORY --bucket BUCKET [--prefix PREFIX]" >&2
}

while (($#)); do
  case "$1" in
    --backup)
      backup=${2:-}
      shift 2
      ;;
    --bucket)
      bucket=${2:-}
      shift 2
      ;;
    --prefix)
      prefix=${2:-}
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$backup" || -z "$bucket" || ! -d "$backup" ]]; then
  usage
  exit 2
fi
if [[ ! "$prefix" =~ ^[A-Za-z0-9._/-]+$ || "$prefix" == /* || "$prefix" == *..* ]]; then
  echo "Backup prefix must be a safe relative S3 prefix." >&2
  exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
backup=$(cd "$backup" && pwd -P)
backup_name=$(basename "$backup")
if [[ ! "$backup_name" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Backup directory name is unsafe: $backup_name" >&2
  exit 2
fi

cd "$repo_root"
python scripts/recovery_manifest.py verify --directory "$backup" >/dev/null
scripts/verify_s3_targets.sh "$bucket" >/dev/null

temporary=$(mktemp -d)
cleanup() {
  rm -rf "$temporary"
}
trap cleanup EXIT
archive="$temporary/$backup_name.tar.gz"
checksum_file="$archive.sha256"
tar -C "$(dirname "$backup")" -czf "$archive" "$backup_name"
checksum=$(sha256sum "$archive" | awk '{print $1}')
printf '%s  %s\n' "$checksum" "$backup_name.tar.gz" >"$checksum_file"

key="${prefix%/}/$backup_name.tar.gz"
aws s3 cp "$archive" "s3://$bucket/$key" \
  --only-show-errors \
  --sse AES256 \
  --metadata "sha256=$checksum"
aws s3 cp "$checksum_file" "s3://$bucket/$key.sha256" \
  --only-show-errors \
  --sse AES256
remote_checksum=$(aws s3api head-object \
  --bucket "$bucket" \
  --key "$key" \
  --query 'Metadata.sha256' \
  --output text)
if [[ "$remote_checksum" != "$checksum" ]]; then
  echo "Uploaded recovery bundle checksum metadata did not match." >&2
  exit 1
fi
echo "Verified off-host recovery bundle: s3://$bucket/$key"
