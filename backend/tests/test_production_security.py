import pytest

from app.core.config import Settings, validate_production_settings


SECURE_PRODUCTION = {
    "environment": "production",
    "secret_key": "a-secure-production-secret-with-more-than-32-characters",
    "session_cookie_secure": True,
    "backend_cors_origins": ["https://os.ironhousecivil.com"],
    "bootstrap_admin_email": "admin@ironhousecontracting.com",
    "bootstrap_admin_password": "temporary-production-password-2026",
}


def test_secure_production_configuration_is_accepted() -> None:
    validate_production_settings(Settings(**SECURE_PRODUCTION))


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"secret_key": "change-me-in-development"}, "SECRET_KEY"),
        ({"session_cookie_secure": False}, "SESSION_COOKIE_SECURE"),
        ({"backend_cors_origins": ["*"]}, "BACKEND_CORS_ORIGINS"),
        ({"bootstrap_admin_email": "admin@example.com"}, "BOOTSTRAP_ADMIN_EMAIL"),
        (
            {"bootstrap_admin_password": "replace-with-a-long-random-login-password"},
            "BOOTSTRAP_ADMIN_PASSWORD",
        ),
    ],
)
def test_insecure_production_configuration_fails_closed(
    override: dict[str, object],
    expected: str,
) -> None:
    values = SECURE_PRODUCTION | override

    with pytest.raises(RuntimeError, match=expected):
        validate_production_settings(Settings(**values))


def test_development_defaults_remain_available_for_local_work() -> None:
    validate_production_settings(Settings())


def test_enabled_production_onboarding_email_requires_secure_mail_settings() -> None:
    values = SECURE_PRODUCTION | {"onboarding_email_delivery_enabled": True}

    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        validate_production_settings(Settings(**values))


def test_enabled_production_onboarding_email_accepts_protected_tls_configuration() -> None:
    values = SECURE_PRODUCTION | {
        "onboarding_email_delivery_enabled": True,
        "smtp_host": "smtp.ironhousecontracting.com",
        "smtp_username": "onboarding@ironhousecontracting.com",
        "smtp_password": "protected-mail-password",
        "smtp_from_email": "onboarding@ironhousecontracting.com",
        "smtp_starttls": True,
    }

    validate_production_settings(Settings(**values))
