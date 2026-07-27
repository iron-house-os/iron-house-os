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
login_file="$smoke_dir/login.json"

trap 'rm -rf "$smoke_dir"' EXIT

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

  STAGING_EMAIL="$STAGING_EMAIL" STAGING_PASSWORD="$STAGING_PASSWORD" python - <<'PY' > "$login_file"
import json
import os

print(json.dumps({"email": os.environ["STAGING_EMAIL"], "password": os.environ["STAGING_PASSWORD"]}))
PY

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

  request \
    "$API_URL$API_PREFIX/auth/logout" \
    "204" \
    --cookie "$cookie_file" \
    --cookie-jar "$cookie_file" \
    --request POST
  request "$API_URL$API_PREFIX/auth/me" "401" --cookie "$cookie_file"
fi

echo "Staging smoke tests passed."
