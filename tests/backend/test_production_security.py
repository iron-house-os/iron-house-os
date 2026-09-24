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


def test_staging_cannot_select_live_quickbooks_or_live_approval() -> None:
    with pytest.raises(RuntimeError, match="QUICKBOOKS_ENVIRONMENT=production"):
        validate_production_settings(
            Settings(
                environment="staging",
                quickbooks_environment="production",
                quickbooks_live_read_only_approved=True,
            )
        )


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


def test_live_quickbooks_fails_closed_without_separate_read_only_approval() -> None:
    values = SECURE_PRODUCTION | {
        "quickbooks_enabled": True,
        "quickbooks_environment": "production",
        "quickbooks_client_id": "production-client-id",
        "quickbooks_client_secret": "production-client-secret-value",
        "quickbooks_token_encryption_key": "production-token-key-with-enough-length",
        "quickbooks_redirect_uri": (
            "https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback"
        ),
        "quickbooks_frontend_return_url": "https://os.ironhousecivil.com/finance",
    }

    with pytest.raises(RuntimeError, match="QUICKBOOKS_LIVE_READ_ONLY_APPROVED"):
        validate_production_settings(Settings(**values))


def test_live_quickbooks_accepts_explicit_read_only_approval_and_secure_settings() -> None:
    values = SECURE_PRODUCTION | {
        "quickbooks_enabled": True,
        "quickbooks_environment": "production",
        "quickbooks_live_read_only_approved": True,
        "quickbooks_client_id": "production-client-id",
        "quickbooks_client_secret": "production-client-secret-value",
        "quickbooks_token_encryption_key": "production-token-key-with-enough-length",
        "quickbooks_redirect_uri": (
            "https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback"
        ),
        "quickbooks_frontend_return_url": "https://os.ironhousecivil.com/finance",
    }

    validate_production_settings(Settings(**values))


def test_database_managed_live_quickbooks_still_requires_secure_redirects_and_token_key() -> None:
    values = SECURE_PRODUCTION | {
        "quickbooks_enabled": False,
        "quickbooks_environment": "production",
        "quickbooks_live_read_only_approved": True,
        "quickbooks_token_encryption_key": "too-short",
        "quickbooks_redirect_uri": (
            "http://localhost:8000/api/v1/finance/quickbooks/oauth/callback"
        ),
        "quickbooks_frontend_return_url": "http://localhost:5173/finance",
    }

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(Settings(**values))

    message = str(exc_info.value)
    assert "QUICKBOOKS_TOKEN_ENCRYPTION_KEY" in message
    assert "QUICKBOOKS_REDIRECT_URI" in message
    assert "QUICKBOOKS_FRONTEND_RETURN_URL" in message


def test_database_managed_live_quickbooks_accepts_secure_callback_without_env_credentials() -> None:
    values = SECURE_PRODUCTION | {
        "quickbooks_enabled": False,
        "quickbooks_environment": "production",
        "quickbooks_live_read_only_approved": True,
        "quickbooks_token_encryption_key": "production-token-key-with-enough-length",
        "quickbooks_redirect_uri": (
            "https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback"
        ),
        "quickbooks_frontend_return_url": "https://os.ironhousecivil.com/finance",
    }

    validate_production_settings(Settings(**values))


def test_live_quickbooks_rejects_unapproved_https_origins_and_paths() -> None:
    values = SECURE_PRODUCTION | {
        "quickbooks_enabled": False,
        "quickbooks_environment": "production",
        "quickbooks_live_read_only_approved": True,
        "quickbooks_token_encryption_key": "production-token-key-with-enough-length",
        "quickbooks_redirect_uri": (
            "https://staging.os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback"
        ),
        "quickbooks_frontend_return_url": "https://unrelated.example/finance",
    }

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(Settings(**values))

    message = str(exc_info.value)
    assert "QUICKBOOKS_REDIRECT_URI must match" in message
    assert "QUICKBOOKS_FRONTEND_RETURN_URL must match" in message


def test_live_quickbooks_rejects_whitespace_around_pinned_urls() -> None:
    values = SECURE_PRODUCTION | {
        "quickbooks_enabled": False,
        "quickbooks_environment": "production",
        "quickbooks_live_read_only_approved": True,
        "quickbooks_token_encryption_key": "production-token-key-with-enough-length",
        "quickbooks_redirect_uri": (
            " https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback"
        ),
        "quickbooks_frontend_return_url": "https://os.ironhousecivil.com/finance ",
    }

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(Settings(**values))

    message = str(exc_info.value)
    assert "QUICKBOOKS_REDIRECT_URI must match" in message
    assert "QUICKBOOKS_FRONTEND_RETURN_URL must match" in message


def test_live_quickbooks_approval_cannot_be_set_for_sandbox() -> None:
    values = SECURE_PRODUCTION | {
        "quickbooks_environment": "sandbox",
        "quickbooks_live_read_only_approved": True,
    }

    with pytest.raises(RuntimeError, match="may only be true"):
        validate_production_settings(Settings(**values))
