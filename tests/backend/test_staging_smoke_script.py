from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_staging_smoke_uses_current_health_and_api_routes() -> None:
    script = (ROOT / "scripts/staging-smoke-test.sh").read_text()

    assert 'request "$WEB_URL/healthz" "200"' in script
    assert 'request "$API_URL/health" "200"' in script
    assert 'request "$API_URL/readiness" "200"' in script
    assert 'API_PREFIX="${API_PREFIX:-/api/v1}"' in script
    assert '"$API_URL$API_PREFIX/$path"' in script
    assert '"$API_URL/$path"' not in script


def test_staging_smoke_is_concurrency_safe_and_cleans_credentials() -> None:
    script = (ROOT / "scripts/staging-smoke-test.sh").read_text()

    assert 'smoke_dir="$(mktemp -d)"' in script
    assert "trap 'rm -rf \"$smoke_dir\"' EXIT" in script
    assert "/tmp/iron-house-smoke-body" not in script
    assert 'login_file="$smoke_dir/login.json"' in script
    assert '"$API_URL$API_PREFIX/auth/logout"' in script


def test_authenticated_smoke_is_optional_and_requires_both_credentials() -> None:
    script = (ROOT / "scripts/staging-smoke-test.sh").read_text()

    assert 'if [[ -n "${STAGING_EMAIL:-}" || -n "${STAGING_PASSWORD:-}" ]]; then' in script
    assert "Set both STAGING_EMAIL and STAGING_PASSWORD" in script
    assert 'request "$API_URL$API_PREFIX/auth/me" "200"' in script
    assert 'request "$API_URL$API_PREFIX/auth/me" "401"' in script
