#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:?Set API_URL, for example https://api-staging.example.com}"
WEB_URL="${WEB_URL:?Set WEB_URL, for example https://staging.example.com}"

request() {
  local url="$1"
  local expected="$2"
  local status
  status="$(curl --silent --show-error --location --output /tmp/iron-house-smoke-body --write-out '%{http_code}' "$url")"
  if [[ "$status" != "$expected" ]]; then
    echo "Smoke check failed: $url returned $status; expected $expected" >&2
    cat /tmp/iron-house-smoke-body >&2 || true
    exit 1
  fi
  echo "PASS $url [$status]"
}

request "$WEB_URL" "200"
request "$API_URL/health" "200"

# Protected resources must not be anonymously readable.
for path in projects suppliers rfqs bids documents equipment users; do
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$API_URL/$path")"
  case "$status" in
    401|403) echo "PASS $API_URL/$path rejects anonymous access [$status]" ;;
    *) echo "FAIL $API_URL/$path returned $status; expected 401 or 403" >&2; exit 1 ;;
  esac
done

echo "Staging smoke tests passed."
