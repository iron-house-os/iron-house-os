from datetime import UTC, datetime
from email.message import EmailMessage

from app.core.config import Settings
from app.services import onboarding_email


class FakeSMTP:
    instance: "FakeSMTP | None" = None

    def __init__(self, host: str, port: int, *, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_credentials: tuple[str, str] | None = None
        self.message: EmailMessage | None = None
        FakeSMTP.instance = self

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def ehlo(self) -> None:
        return None

    def starttls(self, *, context: object) -> None:
        assert context is not None
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_credentials = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


def test_onboarding_email_uses_authenticated_tls_and_only_the_bearer_link(monkeypatch) -> None:
    monkeypatch.setattr(onboarding_email.smtplib, "SMTP", FakeSMTP)
    settings = Settings(
        onboarding_email_delivery_enabled=True,
        smtp_host="smtp.test.invalid",
        smtp_port=587,
        smtp_username="onboarding-user",
        smtp_password="protected-test-password",
        smtp_from_email="onboarding@ironhousecontracting.com",
        smtp_starttls=True,
    )

    onboarding_email.send_onboarding_invitation(
        recipient_email="employee@example.com",
        recipient_name="Employee",
        invite_url="https://staging.os.ironhousecivil.com/employee-onboarding/test-bearer",
        expires_at=datetime(2026, 8, 23, 10, tzinfo=UTC),
        settings=settings,
    )

    client = FakeSMTP.instance
    assert client is not None
    assert client.started_tls is True
    assert client.login_credentials == ("onboarding-user", "protected-test-password")
    assert client.message is not None
    body = client.message.get_content()
    assert "test-bearer" in body
    assert "employee@example.com" == client.message["To"]
    for restricted_label in ("SIN", "bank", "tax", "PPE", "competency", "signature"):
        assert restricted_label not in body
