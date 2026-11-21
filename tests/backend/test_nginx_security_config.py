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
    image = re.search(
        r"^FROM nginx:(\d+)\.(\d+)\.(\d+)-alpine@sha256:[0-9a-f]{64}$",
        dockerfile,
        re.MULTILINE,
    )
    assert image is not None
    major, minor, patch = map(int, image.groups())
    assert (major, minor) > (1, 31) or (
        (major, minor) == (1, 31) and patch >= 9
    ) or ((major, minor) == (1, 30) and patch >= 7)
