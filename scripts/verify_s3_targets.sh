#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: scripts/verify_s3_targets.sh BUCKET [BUCKET ...]" >&2
}

if (($# == 0)); then
  usage
  exit 2
fi
command -v aws >/dev/null || {
  echo "The AWS CLI is required." >&2
  exit 1
}
command -v jq >/dev/null || {
  echo "jq is required." >&2
  exit 1
}
: "${AWS_REGION:?AWS_REGION is required}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}"

for bucket in "$@"; do
  if [[ ! "$bucket" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]]; then
    echo "Invalid S3 bucket name: $bucket" >&2
    exit 2
  fi
  aws s3api head-bucket --bucket "$bucket" >/dev/null
  bucket_region=$(aws s3api get-bucket-location \
    --bucket "$bucket" \
    --query LocationConstraint \
    --output text)
  if [[ "$bucket_region" != "$AWS_REGION" ]]; then
    echo "S3 bucket is in $bucket_region, expected $AWS_REGION: $bucket" >&2
    exit 1
  fi
  versioning=$(aws s3api get-bucket-versioning --bucket "$bucket" --query Status --output text)
  if [[ "$versioning" != "Enabled" ]]; then
    echo "S3 bucket versioning is not enabled: $bucket" >&2
    exit 1
  fi
  public_block=$(aws s3api get-public-access-block --bucket "$bucket")
  if ! jq -e '
    .PublicAccessBlockConfiguration |
    .BlockPublicAcls and .IgnorePublicAcls and .BlockPublicPolicy and .RestrictPublicBuckets
  ' >/dev/null <<<"$public_block"; then
    echo "S3 public access is not fully blocked: $bucket" >&2
    exit 1
  fi
  aws s3api get-bucket-encryption --bucket "$bucket" >/dev/null
  echo "Verified private, versioned, encrypted S3 target: $bucket"
done
