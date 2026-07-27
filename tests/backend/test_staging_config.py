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
    assert "docker-compose.production.yml" not in compose
    assert "os.ironhousecivil.com" not in compose
    assert "/etc/iron-house-os/production.env" not in compose


def test_staging_example_contains_no_production_targets_or_real_secrets() -> None:
    example = (ROOT / ".env.staging.example").read_text()

    assert "iron_house_os_staging" in example
    assert "ihos_staging_session" in example
    assert "staging.invalid" in example
    assert "IRON_HOUSE_CHAT_ENABLED=false" in example
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
