#!/usr/bin/env bash
set -euo pipefail

WEB_URL="${WEB_URL:?Set WEB_URL, for example https://staging.example.com}"
API_URL="${API_URL:-$WEB_URL}"
WEB_URL="${WEB_URL%/}"
API_URL="${API_URL%/}"
API_PREFIX="${API_PREFIX:-/api/v1}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-20}"
smoke_dir="$(mktemp -d)"
body_file="$smoke_dir/body"
cookie_file="$smoke_dir/cookies"
viewer_cookie_file="$smoke_dir/viewer-cookies"
login_file="$smoke_dir/login.json"
viewer_login_file="$smoke_dir/viewer-login.json"
viewer_change_file="$smoke_dir/viewer-change.json"
viewer_create_file="$smoke_dir/viewer-create.json"
viewer_denial_file="$smoke_dir/viewer-denial.json"
mvp_quote_file="$smoke_dir/mvp-quote.json"
mvp_status_file="$smoke_dir/mvp-status.json"
mvp_accept_file="$smoke_dir/mvp-accept.json"

trap 'rm -rf "$smoke_dir"' EXIT
umask 077

request() {
  local url="$1"
  local expected="$2"
  shift 2
  local status
  status="$(curl \
    --silent \
    --show-error \
    --max-time "$SMOKE_TIMEOUT_SECONDS" \
    --output "$body_file" \
    --write-out '%{http_code}' \
    "$@" \
    "$url")"
  if [[ "$status" != "$expected" ]]; then
    echo "Smoke check failed: $url returned $status; expected $expected" >&2
    exit 1
  fi
  echo "PASS $url [$status]"
}

request_one_of() {
  local url="$1"
  local expected_a="$2"
  local expected_b="$3"
  local status
  status="$(curl \
    --silent \
    --show-error \
    --max-time "$SMOKE_TIMEOUT_SECONDS" \
    --output "$body_file" \
    --write-out '%{http_code}' \
    "$url")"
  case "$status" in
    "$expected_a"|"$expected_b") echo "PASS $url [$status]" ;;
    *) echo "Smoke check failed: $url returned $status; expected $expected_a or $expected_b" >&2; exit 1 ;;
  esac
}

read_quote_state() {
  local expected_status="$1"
  local job_expectation="$2"
  local expected_quote_id="${3:-}"
  local expected_project_id="${4:-}"
  BODY_FILE="$body_file" \
  EXPECTED_STATUS="$expected_status" \
  JOB_EXPECTATION="$job_expectation" \
  EXPECTED_QUOTE_ID="$expected_quote_id" \
  EXPECTED_PROJECT_ID="$expected_project_id" \
  python - <<'PY'
import json
import os
from uuid import UUID

payload = json.loads(open(os.environ["BODY_FILE"], encoding="utf-8").read())
if payload.get("status") != os.environ["EXPECTED_STATUS"]:
    raise SystemExit(
        f"Expected quote status {os.environ['EXPECTED_STATUS']!r}, got {payload.get('status')!r}."
    )
quote_id = str(UUID(str(payload.get("id"))))
project_id = str(UUID(str(payload.get("project_id"))))
if os.environ["EXPECTED_QUOTE_ID"] and quote_id != os.environ["EXPECTED_QUOTE_ID"]:
    raise SystemExit("Quote ID changed during the synthetic lifecycle.")
if os.environ["EXPECTED_PROJECT_ID"] and project_id != os.environ["EXPECTED_PROJECT_ID"]:
    raise SystemExit("Project ID changed during the synthetic lifecycle.")
job_number = payload.get("job_number")
if os.environ["JOB_EXPECTATION"] == "absent" and job_number is not None:
    raise SystemExit(f"Non-binding quote state unexpectedly has job number {job_number!r}.")
if os.environ["JOB_EXPECTATION"] == "present" and not str(job_number or "").startswith("IH-"):
    raise SystemExit(f"Accepted quote has invalid job number {job_number!r}.")
revision = int(payload.get("record_revision") or 0)
if revision < 1:
    raise SystemExit("Quote revision is missing or invalid.")
print(f"{quote_id}\t{project_id}\t{revision}\t{job_number or ''}")
PY
}

run_mvp_quote_job_checks() {
  local synthetic_suffix="$1"
  local quote_metadata
  local quote_id
  local project_id
  local quote_revision
  local job_number

  SYNTHETIC_SUFFIX="$synthetic_suffix" python - <<'PY' > "$mvp_quote_file"
import json
import os
from datetime import date, timedelta

suffix = os.environ["SYNTHETIC_SUFFIX"]
print(json.dumps({
    "project_name": f"Disposable staging quote-to-job {suffix}",
    "customer_name": f"Synthetic Customer {suffix}",
    "customer_email": f"staging-mvp-{suffix}@example.invalid",
    "site_address": "100 Disposable Staging Way",
    "scope_summary": "Synthetic quote-to-job release gate. No external customer or commitment.",
    "line_items": [{
        "description": "Synthetic civil work",
        "quantity": "1",
        "unit": "LS",
        "unit_price": "1000.00",
    }],
    "assumptions": ["Disposable CI environment only"],
    "exclusions": ["External submission and real construction"],
    "gst_rate": "5.00",
    "quote_date": date.today().isoformat(),
    "valid_until": (date.today() + timedelta(days=30)).isoformat(),
    "notes": f"Release-readiness synthetic record {suffix}",
}))
PY
  request \
    "$API_URL$API_PREFIX/customer-quotes" \
    "201" \
    --cookie "$cookie_file" \
    --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@$mvp_quote_file"
  quote_metadata="$(read_quote_state "draft" "absent")"
  IFS=$'\t' read -r quote_id project_id quote_revision job_number <<< "$quote_metadata"

  QUOTE_REVISION="$quote_revision" python - <<'PY' > "$mvp_status_file"
import json
import os

print(json.dumps({"expected_revision": int(os.environ["QUOTE_REVISION"]), "status": "ready_for_review"}))
PY
  request \
    "$API_URL$API_PREFIX/customer-quotes/$quote_id/issue-status" \
    "200" \
    --cookie "$cookie_file" \
    --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@$mvp_status_file"
  quote_metadata="$(read_quote_state "draft" "absent" "$quote_id" "$project_id")"
  IFS=$'\t' read -r quote_id project_id quote_revision job_number <<< "$quote_metadata"

  QUOTE_REVISION="$quote_revision" python - <<'PY' > "$mvp_status_file"
import json
import os

print(json.dumps({"expected_revision": int(os.environ["QUOTE_REVISION"]), "status": "approved_for_issue"}))
PY
  request \
    "$API_URL$API_PREFIX/customer-quotes/$quote_id/issue-status" \
    "200" \
    --cookie "$cookie_file" \
    --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@$mvp_status_file"
  quote_metadata="$(read_quote_state "draft" "absent" "$quote_id" "$project_id")"
  IFS=$'\t' read -r quote_id project_id quote_revision job_number <<< "$quote_metadata"

  QUOTE_REVISION="$quote_revision" SYNTHETIC_SUFFIX="$synthetic_suffix" python - <<'PY' > "$mvp_status_file"
import json
import os

print(json.dumps({
    "expected_revision": int(os.environ["QUOTE_REVISION"]),
    "status": "issued",
    "issuance_method": "Disposable staging API",
    "issuance_reference": f"Synthetic issue {os.environ['SYNTHETIC_SUFFIX']}",
}))
PY
  request \
    "$API_URL$API_PREFIX/customer-quotes/$quote_id/issue-status" \
    "200" \
    --cookie "$cookie_file" \
    --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@$mvp_status_file"
  quote_metadata="$(read_quote_state "sent" "absent" "$quote_id" "$project_id")"
  IFS=$'\t' read -r quote_id project_id quote_revision job_number <<< "$quote_metadata"

  QUOTE_REVISION="$quote_revision" SYNTHETIC_SUFFIX="$synthetic_suffix" python - <<'PY' > "$mvp_accept_file"
import json
import os

print(json.dumps({
    "expected_revision": int(os.environ["QUOTE_REVISION"]),
    "acceptance_reference": f"Disposable staging acceptance {os.environ['SYNTHETIC_SUFFIX']}",
    "acceptance_note": "Synthetic release gate only; not an external commitment.",
}))
PY
  request \
    "$API_URL$API_PREFIX/customer-quotes/$quote_id/accept" \
    "200" \
    --cookie "$cookie_file" \
    --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@$mvp_accept_file"
  quote_metadata="$(read_quote_state "accepted" "present" "$quote_id" "$project_id")"
  IFS=$'\t' read -r quote_id project_id quote_revision job_number <<< "$quote_metadata"

  request "$API_URL$API_PREFIX/projects/$project_id" "200" --cookie "$cookie_file"
  BODY_FILE="$body_file" EXPECTED_JOB_NUMBER="$job_number" python - <<'PY'
import json
import os

payload = json.loads(open(os.environ["BODY_FILE"], encoding="utf-8").read())
if payload.get("status") != "awarded":
    raise SystemExit(f"Expected awarded project, got {payload.get('status')!r}.")
if payload.get("project_number") != os.environ["EXPECTED_JOB_NUMBER"]:
    raise SystemExit("Awarded project job number differs from accepted quote.")
if not payload.get("workspace_root") or not payload.get("workspace_provisioned_at"):
    raise SystemExit("Awarded project workspace was not provisioned.")
PY

  request "$API_URL$API_PREFIX/projects/$project_id/workspace" "200" --cookie "$cookie_file"
  request "$API_URL$API_PREFIX/projects/$project_id/start-checklist" "200" --cookie "$cookie_file"
  BODY_FILE="$body_file" python - <<'PY'
import json
import os

payload = json.loads(open(os.environ["BODY_FILE"], encoding="utf-8").read())
if payload.get("status") != "not_ready":
    raise SystemExit("New awarded job must begin with launch controls not ready.")
if payload.get("completed_count") != 0 or payload.get("total_count") != 10:
    raise SystemExit("New awarded job does not have the expected ten unchecked start controls.")
PY

  request "$API_URL$API_PREFIX/projects/$project_id/launch-dashboard" "200" --cookie "$cookie_file"
  BODY_FILE="$body_file" EXPECTED_JOB_NUMBER="$job_number" python - <<'PY'
import json
import os

payload = json.loads(open(os.environ["BODY_FILE"], encoding="utf-8").read())
if payload.get("job_number") != os.environ["EXPECTED_JOB_NUMBER"]:
    raise SystemExit("Launch dashboard job number differs from the accepted quote.")
if payload.get("mobilization_status") != "not_ready":
    raise SystemExit("Launch dashboard inferred readiness for a new job.")
if payload.get("checklist_completed_count") != 0 or payload.get("checklist_total_count") != 10:
    raise SystemExit("Launch dashboard checklist summary is incorrect.")
if not payload.get("next_incomplete_control"):
    raise SystemExit("Launch dashboard did not identify the next incomplete control.")
PY
  printf '%s\n' "$project_id"
}

assert_viewer_permissions() {
  BODY_FILE="$body_file" python - <<'PY'
import json
import os

payload = json.loads(open(os.environ["BODY_FILE"], encoding="utf-8").read())
if payload.get("role") != "viewer":
    raise SystemExit(f"Expected a viewer account, received role={payload.get('role')!r}.")
PY
}

write_login_payload() {
  local output="$1"
  local email="$2"
  local password="$3"
  PAYLOAD_EMAIL="$email" PAYLOAD_PASSWORD="$password" python - <<'PY' > "$output"
import json
import os

print(json.dumps({"email": os.environ["PAYLOAD_EMAIL"], "password": os.environ["PAYLOAD_PASSWORD"]}))
PY
}

run_viewer_checks() {
  local email="$1"
  local password="$2"
  local changed_password="${3:-}"
  local restricted_launch_project_id="${4:-}"

  write_login_payload "$viewer_login_file" "$email" "$password"
  request \
    "$API_URL$API_PREFIX/auth/login" \
    "200" \
    --cookie-jar "$viewer_cookie_file" \
    --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@$viewer_login_file"

  if [[ -n "$changed_password" ]]; then
    CURRENT_PASSWORD="$password" NEW_PASSWORD="$changed_password" python - <<'PY' > "$viewer_change_file"
import json
import os

print(json.dumps({
    "current_password": os.environ["CURRENT_PASSWORD"],
    "new_password": os.environ["NEW_PASSWORD"],
}))
PY
    request \
      "$API_URL$API_PREFIX/auth/change-password" \
      "200" \
      --cookie "$viewer_cookie_file" \
      --cookie-jar "$viewer_cookie_file" \
      --header "Content-Type: application/json" \
      --request POST \
      --data-binary "@$viewer_change_file"
  fi

  request \
    "$API_URL$API_PREFIX/auth/me/permissions" \
    "200" \
    --cookie "$viewer_cookie_file"
  assert_viewer_permissions
  request "$API_URL$API_PREFIX/projects" "200" --cookie "$viewer_cookie_file"
  request "$API_URL$API_PREFIX/users" "403" --cookie "$viewer_cookie_file"
  request \
    "$API_URL$API_PREFIX/projects" \
    "403" \
    --cookie "$viewer_cookie_file" \
    --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@$viewer_denial_file"
  if [[ -n "$restricted_launch_project_id" ]]; then
    request \
      "$API_URL$API_PREFIX/projects/$restricted_launch_project_id/launch-dashboard" \
      "403" \
      --cookie "$viewer_cookie_file"
  fi
  request \
    "$API_URL$API_PREFIX/auth/logout" \
    "204" \
    --cookie "$viewer_cookie_file" \
    --cookie-jar "$viewer_cookie_file" \
    --request POST
  request "$API_URL$API_PREFIX/auth/me" "401" --cookie "$viewer_cookie_file"
}

request "$WEB_URL" "200"
request "$WEB_URL/healthz" "200"
request "$API_URL/health" "200"
request "$API_URL/readiness" "200"

# Protected resources must not be anonymously readable.
for path in projects suppliers rfqs bids documents equipment users; do
  request_one_of "$API_URL$API_PREFIX/$path" "401" "403"
done

if [[ -n "${STAGING_EMAIL:-}" || -n "${STAGING_PASSWORD:-}" ]]; then
  if [[ -z "${STAGING_EMAIL:-}" || -z "${STAGING_PASSWORD:-}" ]]; then
    echo "Set both STAGING_EMAIL and STAGING_PASSWORD for authenticated smoke checks." >&2
    exit 1
  fi

  write_login_payload "$login_file" "$STAGING_EMAIL" "$STAGING_PASSWORD"

  request \
    "$API_URL$API_PREFIX/auth/login" \
    "200" \
    --cookie-jar "$cookie_file" \
    --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@$login_file"

  request "$API_URL$API_PREFIX/auth/me" "200" --cookie "$cookie_file"

  for path in projects suppliers rfqs bids documents equipment; do
    request "$API_URL$API_PREFIX/$path" "200" --cookie "$cookie_file"
  done
  request "$API_URL$API_PREFIX/customer-quotes" "200" --cookie "$cookie_file"
  request "$API_URL$API_PREFIX/workflow-drafts" "200" --cookie "$cookie_file"

  if [[ "${STAGING_MVP_SYNTHETIC_DATA:-false}" == "true" && "${STAGING_SYNTHETIC_DATA:-false}" != "true" ]]; then
    echo "STAGING_MVP_SYNTHETIC_DATA requires STAGING_SYNTHETIC_DATA=true for a disposable viewer boundary check." >&2
    exit 1
  fi

  synthetic_mvp_project_id=""

  if [[ "${STAGING_SYNTHETIC_DATA:-false}" == "true" ]]; then
    synthetic_suffix="${STAGING_SYNTHETIC_SUFFIX:-$(date +%s)-$$}"
    if [[ ! "$synthetic_suffix" =~ ^[A-Za-z0-9._-]+$ ]]; then
      echo "STAGING_SYNTHETIC_SUFFIX contains unsupported characters." >&2
      exit 1
    fi
    viewer_email="staging-viewer-${synthetic_suffix}@ironhousecontracting.com"
    viewer_initial_password="Staging-viewer-${synthetic_suffix}-temporary!"
    viewer_accepted_password="Staging-viewer-${synthetic_suffix}-accepted!"
    VIEWER_EMAIL="$viewer_email" VIEWER_PASSWORD="$viewer_initial_password" python - <<'PY' > "$viewer_create_file"
import json
import os

print(json.dumps({
    "email": os.environ["VIEWER_EMAIL"],
    "display_name": "Sprint 1E synthetic viewer",
    "role": "viewer",
    "password": os.environ["VIEWER_PASSWORD"],
}))
PY
    python - <<'PY' > "$viewer_denial_file"
import json

print(json.dumps({"name": "Sprint 1E viewer denial sentinel"}))
PY
    request \
      "$API_URL$API_PREFIX/users" \
      "201" \
      --cookie "$cookie_file" \
      --header "Content-Type: application/json" \
      --request POST \
      --data-binary "@$viewer_create_file"
    if [[ "${STAGING_MVP_SYNTHETIC_DATA:-false}" == "true" ]]; then
      synthetic_mvp_project_id="$(run_mvp_quote_job_checks "$synthetic_suffix" | tail -n 1)"
      echo "PASS disposable quote-to-job lifecycle [$synthetic_mvp_project_id]"
    fi
  elif [[ -n "${STAGING_VIEWER_EMAIL:-}" || -n "${STAGING_VIEWER_PASSWORD:-}" ]]; then
    if [[ -z "${STAGING_VIEWER_EMAIL:-}" || -z "${STAGING_VIEWER_PASSWORD:-}" ]]; then
      echo "Set both STAGING_VIEWER_EMAIL and STAGING_VIEWER_PASSWORD for role checks." >&2
      exit 1
    fi
    python - <<'PY' > "$viewer_denial_file"
import json

print(json.dumps({"name": "Sprint 1E viewer denial sentinel"}))
PY
  fi

  request \
    "$API_URL$API_PREFIX/auth/logout" \
    "204" \
    --cookie "$cookie_file" \
    --cookie-jar "$cookie_file" \
    --request POST
  request "$API_URL$API_PREFIX/auth/me" "401" --cookie "$cookie_file"

  if [[ "${STAGING_SYNTHETIC_DATA:-false}" == "true" ]]; then
    run_viewer_checks "$viewer_email" "$viewer_initial_password" "$viewer_accepted_password" "$synthetic_mvp_project_id"
  elif [[ -n "${STAGING_VIEWER_EMAIL:-}" ]]; then
    run_viewer_checks "$STAGING_VIEWER_EMAIL" "$STAGING_VIEWER_PASSWORD"
  fi
elif [[ "${STAGING_SYNTHETIC_DATA:-false}" == "true" || "${STAGING_MVP_SYNTHETIC_DATA:-false}" == "true" ]]; then
  echo "Synthetic staging data requires STAGING_EMAIL and STAGING_PASSWORD." >&2
  exit 1
fi

echo "Staging smoke tests passed."
