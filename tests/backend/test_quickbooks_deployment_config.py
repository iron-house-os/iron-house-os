from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CALLBACK = "/api/v1/finance/quickbooks/oauth/callback"
QUICKBOOKS_SETTINGS = (
    "QUICKBOOKS_ENABLED",
    "QUICKBOOKS_ENVIRONMENT",
    "QUICKBOOKS_CLIENT_ID",
    "QUICKBOOKS_CLIENT_SECRET",
    "QUICKBOOKS_REDIRECT_URI",
    "QUICKBOOKS_FRONTEND_RETURN_URL",
    "QUICKBOOKS_TOKEN_ENCRYPTION_KEY",
)


def _callback_blocks(source: str) -> list[str]:
    marker = f"location = {CALLBACK} {{"
    blocks: list[str] = []
    offset = 0
    while (start := source.find(marker, offset)) >= 0:
        end = source.find("\n    }", start)
        if end < 0:
            end = source.find("\n  }", start)
        assert end >= 0
        blocks.append(source[start:end])
        offset = end + 1
    return blocks


def test_compose_passes_quickbooks_settings_and_suppresses_backend_access_logs() -> None:
    for relative_path in ("docker-compose.production.yml", "docker-compose.staging.yml"):
        compose = (ROOT / relative_path).read_text()
        for setting in QUICKBOOKS_SETTINGS:
            assert f"{setting}:" in compose
        assert "--no-access-log" in compose

    assert "--no-access-log" in (ROOT / "backend/Dockerfile").read_text()
    assert "--no-access-log" in (ROOT / "docker/backend.Dockerfile").read_text()
    assert "--no-access-log" in (ROOT / "docker-compose.yml").read_text()


def test_all_deployed_proxies_suppress_callback_access_logging() -> None:
    expected_blocks = {
        "frontend/nginx.conf": 1,
        "ops/digitalocean/nginx-live.conf": 2,
        "ops/digitalocean/nginx-staging.conf.template": 2,
    }
    for relative_path, count in expected_blocks.items():
        source = (ROOT / relative_path).read_text()
        blocks = _callback_blocks(source)
        assert len(blocks) == count
        assert all("access_log off;" in block for block in blocks)
        assert all("error_log /dev/null crit;" in block for block in blocks)
        assert all('add_header Referrer-Policy "no-referrer" always;' in block for block in blocks)


def test_staging_environment_generator_keeps_quickbooks_disabled_with_exact_host_urls() -> None:
    deploy = (ROOT / "ops/digitalocean/staging-deploy.sh").read_text()

    assert 'echo "QUICKBOOKS_ENABLED=false"' in deploy
    assert 'echo "QUICKBOOKS_ENVIRONMENT=sandbox"' in deploy
    assert (
        'echo "QUICKBOOKS_REDIRECT_URI=https://$staging_host'
        f'{CALLBACK}"'
    ) in deploy
    assert 'echo "QUICKBOOKS_FRONTEND_RETURN_URL=https://$staging_host/finance"' in deploy
