import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "path",
    [
        "ops/digitalocean/nginx-live.conf",
        "ops/digitalocean/nginx-staging.conf.template",
        "ops/digitalocean/nginx-maintenance.conf",
        "frontend/nginx.conf",
    ],
)
def test_nginx_configs_do_not_enable_http2(path: str) -> None:
    config = re.sub(r"#[^\n]*", "", (ROOT / path).read_text())
    assert not re.search(r"\blisten\b[^;]*\bhttp2\b", config)
    assert not re.search(r"\bhttp2\s+on\s*;", config)


def test_frontend_uses_patched_immutable_nginx_image() -> None:
    dockerfile = (ROOT / "frontend/Dockerfile").read_text()
    stages = re.findall(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE | re.IGNORECASE)
    assert stages[-1] == (
        "nginx:1.30.7-alpine@sha256:"
        "caf4e1e032a20f9c3c5e28fc7f25ffd768ad8677b4975c54193075997b3a97e3"
    )
    assert 'RUN test "$(nginx -v 2>&1)" = "nginx version: nginx/1.30.7"' in dockerfile


def test_cutover_recovery_preserves_security_and_verifies_runtime() -> None:
    cutover = (ROOT / "ops/digitalocean/cutover.sh").read_text()
    recovery = cutover.split("rollback_maintenance() {", 1)[1].split("trap rollback_maintenance", 1)[0]
    assert "ops/digitalocean/nginx-live.conf" in recovery
    assert "ops/digitalocean/nginx-maintenance.conf" in recovery
    assert "previous_gateway" not in recovery
    assert 'python3 scripts/patch_nginx_host.py' in cutover
    assert cutover.index("scripts/scheduled_backup.sh") < cutover.index("python3 scripts/patch_nginx_host.py")
    assert cutover.index("python3 scripts/patch_nginx_host.py") < cutover.index("gateway_mutated=1")
    assert 'exec -T frontend nginx -v' in cutover
    assert "frontend_image_id=$(docker inspect" in cutover
