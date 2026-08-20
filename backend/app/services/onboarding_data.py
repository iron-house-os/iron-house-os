"""Authenticated encryption for restricted employee onboarding form data."""

from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.employee_onboarding import PortalPacket


class OnboardingDataUnavailable(RuntimeError):
    """Raised when restricted onboarding data cannot be safely decrypted."""


def encrypt_packet(packet: PortalPacket) -> str:
    payload = packet.model_dump(mode="json")
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _cipher().encrypt(encoded).decode("ascii")


def decrypt_packet(encrypted: str | None) -> PortalPacket:
    if not encrypted:
        return PortalPacket()
    try:
        decoded = _cipher().decrypt(encrypted.encode("ascii"))
        return PortalPacket.model_validate_json(decoded)
    except (InvalidToken, UnicodeDecodeError, ValidationError) as exc:
        raise OnboardingDataUnavailable(
            "The restricted onboarding packet cannot be decrypted. Administrator review is required."
        ) from exc


def _cipher() -> Fernet:
    source = get_settings().secret_key
    context = b"iron-house-os:employee-onboarding:v1:"
    key = base64.urlsafe_b64encode(hashlib.sha256(context + source.encode("utf-8")).digest())
    return Fernet(key)
