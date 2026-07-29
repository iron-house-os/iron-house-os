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
    run_viewer_checks "$viewer_email" "$viewer_initial_password" "$viewer_accepted_password"
  elif [[ -n "${STAGING_VIEWER_EMAIL:-}" ]]; then
    run_viewer_checks "$STAGING_VIEWER_EMAIL" "$STAGING_VIEWER_PASSWORD"
  fi
elif [[ "${STAGING_SYNTHETIC_DATA:-false}" == "true" ]]; then
  echo "STAGING_SYNTHETIC_DATA requires STAGING_EMAIL and STAGING_PASSWORD." >&2
  exit 1
fi

echo "Staging smoke tests passed."
