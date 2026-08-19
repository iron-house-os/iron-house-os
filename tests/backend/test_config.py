from pathlib import Path

from app.core.config import Settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_checked_in_backend_env_example_is_accepted() -> None:
    settings = Settings(_env_file=REPOSITORY_ROOT / "backend" / ".env.example")

    assert settings.environment == "development"
    assert settings.session_cookie_secure is False
    assert settings.backend_cors_origins == ["http://localhost:5173"]
