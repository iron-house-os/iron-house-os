#!/usr/bin/env bash
set -euo pipefail
umask 077

release_sha=
bundle_file=
evidence_file=

usage() {
  echo "Usage: ihos-production-awarded-invoice-import --release 40_HEX_SHA --bundle ops/production-awarded-invoice-imports/FILE.json --evidence FILE" >&2
}

while (($#)); do
  case "$1" in
    --release)
      release_sha=${2:-}
      shift 2
      ;;
    --bundle)
      bundle_file=${2:-}
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

if ((EUID != 0)) ||
  [[ ! "$release_sha" =~ ^[0-9a-f]{40}$ ]] ||
  [[ ! "$bundle_file" =~ ^ops/production-awarded-invoice-imports/[A-Za-z0-9._-]+\.json$ ]] ||
  [[ -z "$evidence_file" ]]; then
  usage
  exit 2
fi
if [[ "$(hostname)" != "iron-house-os-prod-1" ]]; then
  echo "Refusing production import on unexpected host." >&2
  exit 1
fi

release_root="/opt/iron-house-os-releases/$release_sha"
if [[ ! -d "$release_root/.git" ]]; then
  echo "The requested release has not been installed through the approved production deployment workflow." >&2
  exit 1
fi
git_release() {
  git -c "safe.directory=$release_root" -C "$release_root" "$@"
}
if [[ "$(git_release rev-parse HEAD)" != "$release_sha" ]] || [[ -n "$(git_release status --porcelain)" ]]; then
  echo "Immutable production release checkout is missing, dirty, or has the wrong SHA." >&2
  exit 1
fi
remote_url=$(git_release remote get-url origin)
case "$remote_url" in
  https://github.com/iron-house-os/iron-house-os|https://github.com/iron-house-os/iron-house-os.git|git@github.com:iron-house-os/iron-house-os.git)
    ;;
  *)
    echo "Unexpected repository remote: $remote_url" >&2
    exit 1
    ;;
esac
git_release fetch --quiet origin main
if ! git_release merge-base --is-ancestor "$release_sha" origin/main; then
  echo "Requested release is not present on origin/main." >&2
  exit 1
fi

bundle_path="$release_root/$bundle_file"
importer_path="$release_root/ops/scripts/production_awarded_invoice_import.py"
if [[ ! -f "$bundle_path" || ! -f "$importer_path" ]]; then
  echo "Approved release is missing the import bundle or importer." >&2
  exit 1
fi
resolved_bundle=$(realpath "$bundle_path")
if [[ "$resolved_bundle" != "$release_root/ops/production-awarded-invoice-imports/"*.json ]]; then
  echo "Import bundle escaped the approved release directory." >&2
  exit 1
fi
if ! git_release diff --quiet HEAD -- "$bundle_file" "ops/scripts/production_awarded_invoice_import.py"; then
  echo "Import bundle or importer differs from the approved release." >&2
  exit 1
fi

evidence_parent=$(cd "$(dirname "$evidence_file")" && pwd -P)
evidence_name=$(basename "$evidence_file")
if [[ "$evidence_parent" != "/opt/iron-house-os-actions-runner/_work/_temp" &&
      "$evidence_parent" != /opt/iron-house-os-actions-runner/_work/_temp/* ]] ||
  [[ ! "$evidence_name" =~ ^[A-Za-z0-9._-]+\.json$ ]]; then
  echo "Evidence output must be a JSON file in the restricted runner temporary directory." >&2
  exit 1
fi
evidence_file="$evidence_parent/$evidence_name"

environment_file=/etc/iron-house-os/production.env
if [[ "$(stat -c '%U:%G:%a' "$environment_file" 2>/dev/null || true)" != "root:root:600" &&
      "$(stat -c '%U:%G:%a' "$environment_file" 2>/dev/null || true)" != "root:root:400" ]]; then
  echo "Protected production environment ownership or permissions are invalid." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$environment_file"
set +a
: "${BOOTSTRAP_ADMIN_EMAIL:?BOOTSTRAP_ADMIN_EMAIL is required}"
: "${BOOTSTRAP_ADMIN_PASSWORD:?BOOTSTRAP_ADMIN_PASSWORD is required}"
IHOS_PORT=${IHOS_PORT:-8080}

readiness_url="http://127.0.0.1:${IHOS_PORT}/readiness"
curl --fail --silent --show-error --connect-timeout 5 --max-time 30 "$readiness_url" |
  EXPECTED_RELEASE="$release_sha" python3 -c '
import json, os, sys
payload = json.load(sys.stdin)
expected = os.environ["EXPECTED_RELEASE"]
release_id = payload.get("checks", {}).get("release_id")
if payload.get("status") != "ready" or release_id != expected:
    raise SystemExit(
        "Production release mismatch: status={}, release_id={}, expected={}".format(
            payload.get("status"), release_id, expected
        )
    )
'

temporary_evidence=$(mktemp "$evidence_parent/.production-awarded-invoice-import.XXXXXX")
trap 'rm -f "$temporary_evidence"' EXIT
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  IHOS_PORT="$IHOS_PORT" \
  BOOTSTRAP_ADMIN_EMAIL="$BOOTSTRAP_ADMIN_EMAIL" \
  BOOTSTRAP_ADMIN_PASSWORD="$BOOTSTRAP_ADMIN_PASSWORD" \
  python3 "$importer_path" import \
    --input "$resolved_bundle" \
    --evidence "$temporary_evidence"

python3 -m json.tool "$temporary_evidence" >/dev/null
install -o ihos-runner -g ihos-runner -m 0640 "$temporary_evidence" "$evidence_file"
trap - EXIT
rm -f "$temporary_evidence"
echo "Production awarded-invoice import verified for release $release_sha."
