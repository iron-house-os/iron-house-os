"""Server-confirmed email delivery for onboarding bearer invitations."""

from __future__ import annotations

import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings, get_settings


class OnboardingEmailDeliveryError(RuntimeError):
    """Raised without leaking provider details or the bearer invitation."""


def send_onboarding_invitation(
    *,
    recipient_email: str,
    recipient_name: str,
    invite_url: str,
    expires_at: datetime,
    settings: Settings | None = None,
) -> None:
    config = settings or get_settings()
    if not config.onboarding_email_delivery_enabled:
        raise OnboardingEmailDeliveryError("delivery_disabled")

    message = EmailMessage()
    message["Subject"] = "Iron House employee onboarding invitation"
    message["From"] = formataddr((config.smtp_from_name, config.smtp_from_email or ""))
    message["To"] = recipient_email
    message.set_content(
        f"Hello {recipient_name},\n\n"
        "Complete your secure Iron House onboarding forms using the link below.\n\n"
        f"{invite_url}\n\n"
        f"This invitation expires {expires_at.isoformat()}. "
        "It is personal and must not be forwarded.\n\n"
        "Iron House Contracting"
    )

    try:
        if config.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                config.smtp_host or "",
                config.smtp_port,
                timeout=config.smtp_timeout_seconds,
                context=ssl.create_default_context(),
            ) as client:
                _authenticate_and_send(client, message, config)
        else:
            with smtplib.SMTP(
                config.smtp_host or "",
                config.smtp_port,
                timeout=config.smtp_timeout_seconds,
            ) as client:
                client.ehlo()
                if config.smtp_starttls:
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                _authenticate_and_send(client, message, config)
    except (OSError, smtplib.SMTPException) as exc:
        raise OnboardingEmailDeliveryError("provider_rejected") from exc


def _authenticate_and_send(client: smtplib.SMTP, message: EmailMessage, settings: Settings) -> None:
    if settings.smtp_username:
        client.login(settings.smtp_username, settings.smtp_password or "")
    client.send_message(message)
