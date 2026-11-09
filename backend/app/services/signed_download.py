from dataclasses import dataclass
import hashlib
import hmac
import os
import time
from uuid import UUID

DEFAULT_TTL_SECONDS = 300


@dataclass(frozen=True)
class SignedDownloadToken:
    document_id: UUID
    expires_at: int
    signature: str

    def encode(self) -> str:
        return f"{self.document_id}.{self.expires_at}.{self.signature}"


def _secret() -> bytes:
    return os.getenv("IHOS_DOWNLOAD_SIGNING_SECRET", "development-only-secret").encode("utf-8")


def _signature(document_id: UUID, expires_at: int) -> str:
    payload = f"{document_id}.{expires_at}".encode("utf-8")
    return hmac.new(_secret(), payload, hashlib.sha256).hexdigest()


def create_download_token(
    document_id: UUID,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: int | None = None,
) -> str:
    issued_at = int(time.time()) if now is None else now
    expires_at = issued_at + ttl_seconds
    return SignedDownloadToken(
        document_id=document_id,
        expires_at=expires_at,
        signature=_signature(document_id, expires_at),
    ).encode()


def verify_download_token(token: str, now: int | None = None) -> UUID:
    try:
        raw_document_id, raw_expires_at, signature = token.split(".", maxsplit=2)
        document_id = UUID(raw_document_id)
        expires_at = int(raw_expires_at)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid download token") from exc

    expected = _signature(document_id, expires_at)
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid download token signature")

    current_time = int(time.time()) if now is None else now
    if expires_at < current_time:
        raise ValueError("Download token has expired")

    return document_id
