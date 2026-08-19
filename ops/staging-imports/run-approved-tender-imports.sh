#!/usr/bin/env bash
set -Eeuo pipefail

: "${RELEASE_SHA:?RELEASE_SHA is required}"
: "${EVIDENCE_DIR:?EVIDENCE_DIR is required}"
: "${IHOS_IMPORT_OPERATOR:?IHOS_IMPORT_OPERATOR is required}"

readonly STACK_FILE="${GITHUB_WORKSPACE}/docker-compose.staging.yml"
readonly STACK_NAME="iron-house-os-staging"
readonly STAGING_ENV="/etc/iron-house-os/staging.env"
readonly READINESS_URL="https://staging.os.ironhousecivil.com/readiness"
readonly HEALTH_URL="https://staging.os.ironhousecivil.com/health"

mkdir -p "$EVIDENCE_DIR"
cp ops/staging-imports/2026-08-19-issues-129-132-134.json "$EVIDENCE_DIR/approval-marker.json"

compose=(
  sudo env "IHOS_STAGING_RELEASE_ID=$RELEASE_SHA"
  docker compose
  --env-file "$STAGING_ENV"
  -f "$STACK_FILE"
  -p "$STACK_NAME"
)

read_live_release() {
  local payload
  payload="$(curl --fail --silent --show-error "$READINESS_URL")" || return 1
  READINESS_JSON="$payload" python3 - <<'PY'
import json
import os

print(json.loads(os.environ["READINESS_JSON"]).get("checks", {}).get("release_id", ""))
PY
}

live_release=""
for attempt in $(seq 1 120); do
  live_release="$(read_live_release || true)"
  if [[ "$live_release" == "$RELEASE_SHA" ]]; then
    break
  fi
  sleep 10
done
if [[ "$live_release" != "$RELEASE_SHA" ]]; then
  printf 'Staging did not reach approved release %s; last observed %s\n' "$RELEASE_SHA" "$live_release" >&2
  exit 1
fi

curl --fail --silent --show-error "$READINESS_URL" | tee "$EVIDENCE_DIR/readiness-before.json"
curl --fail --silent --show-error "$HEALTH_URL" | tee "$EVIDENCE_DIR/health-before.json"

run_import() {
  local label="$1"
  local module="$2"
  local expected_status="$3"
  shift 3
  local output="$EVIDENCE_DIR/${label}.json"

  "${compose[@]}" exec -T backend     python -m "$module"       --operator "$IHOS_IMPORT_OPERATOR"       "$@" | tee "$output"

  python3 - "$output" "$expected_status" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
expected = sys.argv[2]
payload = json.loads(path.read_text(encoding="utf-8"))
actual = payload.get("status")
if actual != expected:
    raise SystemExit(f"{path.name}: expected status {expected!r}, got {actual!r}")
PY
}

run_import "01-drive-dry-run" "app.tools.drive_tender_import" "dry_run"
run_import "02-drive-apply" "app.tools.drive_tender_import" "applied" --apply
run_import "03-drive-idempotency-apply" "app.tools.drive_tender_import" "applied" --apply

run_import "04-fernie-dry-run" "app.tools.fernie_staging_import" "dry_run"
run_import "05-fernie-apply" "app.tools.fernie_staging_import" "applied"   --apply   --confirm-expired-intake
run_import "06-fernie-idempotency-apply" "app.tools.fernie_staging_import" "applied"   --apply   --confirm-expired-intake

run_import "07-fuel-estimates-dry-run" "app.tools.fuel_estimate_staging_import" "dry_run"
run_import "08-fuel-estimates-apply" "app.tools.fuel_estimate_staging_import" "applied"   --apply   --confirm-provisional-estimates   --confirm-expired-intake
run_import "09-fuel-estimates-idempotency-apply" "app.tools.fuel_estimate_staging_import" "applied"   --apply   --confirm-provisional-estimates   --confirm-expired-intake

curl --fail --silent --show-error "$HEALTH_URL" | tee "$EVIDENCE_DIR/health-after.json"
curl --fail --silent --show-error "$READINESS_URL" | tee "$EVIDENCE_DIR/readiness-after.json"
final_release="$(read_live_release)"
test "$final_release" = "$RELEASE_SHA"

printf '%s\n' "$RELEASE_SHA" >"$EVIDENCE_DIR/release-sha.txt"
