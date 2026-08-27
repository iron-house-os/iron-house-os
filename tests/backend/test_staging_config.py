from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_staging_compose_is_standalone_and_production_isolated() -> None:
    compose = (ROOT / "docker-compose.staging.yml").read_text()

    assert "name: iron-house-os-staging" in compose
    assert "ENVIRONMENT: staging" in compose
    assert '127.0.0.1:${IHOS_STAGING_PORT:-8081}:80' in compose
    assert "iron-house-os-staging-postgres-data" in compose
    assert "iron-house-os-staging-backend-data" in compose
    assert "iron-house-os-staging-network" in compose
    assert "SESSION_COOKIE_NAME" in compose
    assert "IHOS_STAGING_RELEASE_ID" in compose
    assert "VITE_HEY_CHAT_VOICE_ENABLED" not in compose
    assert "VITE_PERFORMANCE_OBSERVABILITY_ENABLED" in compose
    assert "docker-compose.production.yml" not in compose
    assert "os.ironhousecivil.com" not in compose
    assert "/etc/iron-house-os/production.env" not in compose


def test_staging_example_contains_no_production_targets_or_real_secrets() -> None:
    example = (ROOT / ".env.staging.example").read_text()

    assert "iron_house_os_staging" in example
    assert "ihos_staging_session" in example
    assert "staging.invalid" in example
    assert "IRON_HOUSE_CHAT_ENABLED=false" in example
    assert "VITE_HEY_CHAT_VOICE_ENABLED" not in example
    assert "VITE_PERFORMANCE_OBSERVABILITY_ENABLED=false" in example
    assert "os.ironhousecivil.com" not in example
    assert "jeremie@" not in example


def test_staging_wrapper_pins_safe_compose_inputs() -> None:
    wrapper = (ROOT / "scripts/staging-compose.sh").read_text()

    assert 'compose_file="$root_dir/docker-compose.staging.yml"' in wrapper
    assert 'project_name="iron-house-os-staging"' in wrapper
    assert 'env_file="${IHOS_STAGING_ENV_FILE:-$root_dir/.env.staging}"' in wrapper
    assert "Refusing to use a production environment file for staging." in wrapper
    assert "docker-compose.yml" not in wrapper
    assert "docker-compose.production.yml" not in wrapper


def test_staging_nginx_template_cannot_target_production_by_default() -> None:
    nginx = (ROOT / "ops/digitalocean/nginx-staging.conf.template").read_text()

    assert "${IHOS_STAGING_HOST}" in nginx
    assert "proxy_pass http://127.0.0.1:8081;" in nginx
    assert "os.ironhousecivil.com" not in nginx


def test_live_staging_deploy_is_isolated_and_keeps_secrets_on_host() -> None:
    deploy = (ROOT / "ops/digitalocean/staging-deploy.sh").read_text()

    assert 'staging_host" != "staging.os.ironhousecivil.com"' in deploy
    assert "docker-compose.production.yml" not in deploy
    assert "/etc/iron-house-os/production.env" in deploy
    assert "Refusing to use a production environment file for staging." in deploy
    assert "com.docker.compose.project=iron-house-os-staging" in deploy
    assert "Port 8081 is already in use by a non-staging workload." in deploy
    assert "openssl rand" in deploy
    assert "chmod 0600" in deploy
    assert "IRON_HOUSE_CHAT_ENABLED=false" in deploy
    assert "GOOGLE_CALENDAR_ENABLED=false" in deploy
    assert "VITE_HEY_CHAT_VOICE_ENABLED" not in deploy
    assert "VITE_PERFORMANCE_OBSERVABILITY_ENABLED=true" in deploy
    assert "certbot certonly --nginx" in deploy
    assert "--agree-tos" not in deploy
    assert "production_comparison" in deploy
    assert "read_only" in deploy


def test_release_workflow_uses_disposable_staging_and_immutable_evidence() -> None:
    workflow = (ROOT / ".github/workflows/release-readiness.yml").read_text()

    assert workflow.count('- ".github/workflows/staging-deploy.yml"') == 2
    assert "Disposable staging smoke, rollback, and evidence" in workflow
    assert "scripts/staging-smoke-test.sh" in workflow
    assert "STAGING_SYNTHETIC_DATA: \"true\"" in workflow
    assert "STAGING_MVP_SYNTHETIC_DATA: \"true\"" in workflow
    assert "scripts/staging_rollback_probe.py verify-absent" in workflow
    assert "--profile staging" in workflow
    assert "--production-baseline 55afaa689603263c1ad415436e90cce6679808c3" in workflow
    assert 'backend_image="$(docker image inspect' in workflow


def test_staging_deploy_pins_and_verifies_the_live_release() -> None:
    workflow = (ROOT / ".github/workflows/staging-deploy.yml").read_text()

    assert "Select exact current main for staging" in workflow
    assert 'current_main="$(git rev-parse origin/main)"' in workflow
    assert 'if [[ "$RELEASE_SHA" != "$current_main" ]]' in workflow
    assert 'echo "deploy=false" >> "$GITHUB_OUTPUT"' in workflow
    assert "Skipping stale staging release" in workflow
    assert "if: steps.current_main.outputs.deploy == 'true'" in workflow
    assert 'test "$RELEASE_SHA" = "$(git rev-parse origin/main)"' in workflow
    assert workflow.index('test "$RELEASE_SHA" = "$(git rev-parse origin/main)"') < workflow.index(
        'sudo env IHOS_STAGING_RELEASE_ID="$RELEASE_SHA" docker compose'
    )
    assert 'sudo env IHOS_STAGING_RELEASE_ID="$RELEASE_SHA" docker compose' in workflow
    assert "exec -T backend alembic heads" in workflow
    assert 'test "$migration" = "$expected_migration"' in workflow
    assert 'actual = readiness.get("checks", {}).get("release_id")' in workflow
    assert 'expected = os.environ["RELEASE_SHA"]' in workflow
    assert "if actual != expected:" in workflow


def test_frontend_proxy_exposes_backend_health_without_spa_fallback() -> None:
    nginx = (ROOT / "frontend/nginx.conf").read_text()

    assert "location = /health {" in nginx
    assert "proxy_pass http://backend:8000/health;" in nginx


def test_voice_control_system_is_retired() -> None:
    app = (ROOT / "frontend/src/App.tsx").read_text()
    chat = (ROOT / "frontend/src/pages/IronHouseChatPage.tsx").read_text()

    assert "HandsFreeVoice" not in app
    assert "SpeechRecognition" not in chat
    assert "speechSynthesis" not in chat
    assert not (ROOT / "frontend/src/contexts/HandsFreeVoiceContext.tsx").exists()
    assert not (ROOT / "frontend/src/utils/voiceControls.ts").exists()
    assert not (ROOT / "frontend/src/utils/voiceNavigation.ts").exists()
    assert not (ROOT / "frontend/e2e/voice-acceptance.spec.ts").exists()
    assert (ROOT / "docs/operations/voice-control-retirement.md").is_file()
