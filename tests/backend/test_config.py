from pathlib import Path

import pytest

from app.core.config import Settings, validate_production_settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_checked_in_backend_env_example_is_accepted() -> None:
    settings = Settings(_env_file=REPOSITORY_ROOT / "backend" / ".env.example")

    assert settings.environment == "development"
    assert settings.session_cookie_secure is False
    assert settings.backend_cors_origins == ["http://localhost:5173"]


def _secure_production(**overrides: object) -> Settings:
    values = {
        "environment": "production",
        "secret_key": "a-secure-production-secret-with-more-than-32-characters",
        "session_cookie_secure": True,
        "backend_cors_origins": ["https://os.ironhousecivil.com"],
        "bootstrap_admin_email": "admin@ironhousecontracting.com",
        "bootstrap_admin_password": "temporary-production-password-2026",
        **overrides,
    }
    return Settings(**values)


def test_enabled_onboarding_email_fails_closed_without_protected_smtp() -> None:
    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        validate_production_settings(
            _secure_production(onboarding_email_delivery_enabled=True)
        )


def test_enabled_onboarding_email_accepts_authenticated_tls_smtp() -> None:
    validate_production_settings(
        _secure_production(
            onboarding_email_delivery_enabled=True,
            smtp_host="smtp.ironhousecontracting.com",
            smtp_username="onboarding@ironhousecontracting.com",
            smtp_password="protected-mail-password",
            smtp_from_email="onboarding@ironhousecontracting.com",
            smtp_starttls=True,
        )
    )
