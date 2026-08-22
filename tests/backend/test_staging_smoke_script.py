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


def test_staging_smoke_proves_viewer_role_denials_and_synthetic_opt_in() -> None:
    script = (ROOT / "scripts/staging-smoke-test.sh").read_text()

    assert 'if [[ "${STAGING_SYNTHETIC_DATA:-false}" == "true" ]]; then' in script
    assert '"display_name": "Sprint 1E synthetic viewer"' in script
    assert 'request "$API_URL$API_PREFIX/users" "403"' in script
    assert (
        'request \\\n'
        '    "$API_URL$API_PREFIX/projects" \\\n'
        '    "403"'
    ) in script
    assert "Synthetic staging data requires STAGING_EMAIL and STAGING_PASSWORD" in script
    assert "Set both STAGING_VIEWER_EMAIL and STAGING_VIEWER_PASSWORD" in script


def test_disposable_mvp_smoke_proves_quote_to_job_lifecycle_and_viewer_boundary() -> None:
    script = (ROOT / "scripts/staging-smoke-test.sh").read_text()

    assert 'if [[ "${STAGING_MVP_SYNTHETIC_DATA:-false}" == "true"' in script
    assert "STAGING_MVP_SYNTHETIC_DATA requires STAGING_SYNTHETIC_DATA=true" in script
    assert '"$API_URL$API_PREFIX/customer-quotes"' in script
    assert 'read_quote_state "draft" "absent"' in script
    assert '"status": "ready_for_review"' in script
    assert '"status": "approved_for_issue"' in script
    assert '"status": "issued"' in script
    assert 'customer-quotes/$quote_id/issue-status' in script
    assert 'read_quote_state "sent" "absent"' in script
    assert 'read_quote_state "accepted" "present"' in script
    assert '"$API_URL$API_PREFIX/projects/$project_id/workspace"' in script
    assert '"$API_URL$API_PREFIX/projects/$project_id/start-checklist"' in script
    assert '"$API_URL$API_PREFIX/projects/$project_id/launch-dashboard"' in script
    assert '"$API_URL$API_PREFIX/projects/$restricted_launch_project_id/launch-dashboard"' in script
    assert "New awarded job does not have the expected ten unchecked start controls." in script
    assert "Launch dashboard inferred readiness for a new job." in script


def test_staging_rollback_probe_requires_post_restore_absence() -> None:
    probe = (ROOT / "scripts/staging_rollback_probe.py").read_text()

    assert 'choices=("create", "verify-absent")' in probe
    assert "if exc.code == 404" in probe
    assert '"result": "absent_after_restore"' in probe
