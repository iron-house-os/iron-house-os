from uuid import uuid4

import pytest

from app.services.signed_download import create_download_token, verify_download_token


def test_signed_download_token_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IHOS_DOWNLOAD_SIGNING_SECRET", "test-secret")
    document_id = uuid4()

    token = create_download_token(document_id, ttl_seconds=60, now=1_000)

    assert verify_download_token(token, now=1_030) == document_id


def test_signed_download_token_rejects_tampering(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IHOS_DOWNLOAD_SIGNING_SECRET", "test-secret")
    document_id = uuid4()
    token = create_download_token(document_id, ttl_seconds=60, now=1_000)
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")

    with pytest.raises(ValueError, match="signature"):
        verify_download_token(tampered, now=1_030)


def test_signed_download_token_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IHOS_DOWNLOAD_SIGNING_SECRET", "test-secret")
    token = create_download_token(uuid4(), ttl_seconds=60, now=1_000)

    with pytest.raises(ValueError, match="expired"):
        verify_download_token(token, now=1_061)
