import asyncio
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
import pytest

from app.services import file_storage
from app.services.file_storage import (
    LocalFileStorageProvider,
    S3FileStorageProvider,
    build_storage_provider,
)


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, dict]] = {}
        self.head_bucket_calls: list[str] = []

    def upload_file(self, filename: str, bucket: str, key: str, ExtraArgs: dict) -> None:
        self.objects[(bucket, key)] = (Path(filename).read_bytes(), ExtraArgs)

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        Path(filename).write_bytes(self.objects[(bucket, key)][0])

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        return {"Metadata": self.objects[(Bucket, Key)][1]["Metadata"]}

    def head_bucket(self, *, Bucket: str) -> None:
        self.head_bucket_calls.append(Bucket)


def test_build_storage_provider_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IHOS_STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("IHOS_STORAGE_ROOT", raising=False)

    provider = build_storage_provider()

    assert isinstance(provider, LocalFileStorageProvider)


def test_build_storage_provider_uses_configured_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IHOS_STORAGE_BACKEND", "local")
    monkeypatch.setenv("IHOS_STORAGE_ROOT", str(tmp_path))

    provider = build_storage_provider()

    assert isinstance(provider, LocalFileStorageProvider)
    assert provider.root == tmp_path


def test_build_storage_provider_rejects_unknown_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IHOS_STORAGE_BACKEND", "unknown")

    with pytest.raises(RuntimeError, match="Unsupported IHOS_STORAGE_BACKEND"):
        build_storage_provider()


def test_s3_provider_round_trips_private_object_through_cache(tmp_path: Path) -> None:
    client = FakeS3Client()
    provider = S3FileStorageProvider(
        bucket="private-ihos",
        prefix="production",
        cache_root=tmp_path,
        client=client,
    )
    upload = UploadFile(filename="drawing.pdf", file=BytesIO(b"private drawing content"))

    stored = asyncio.run(provider.store_upload(upload, project_id="project-123"))

    assert stored.storage_uri.startswith("s3://private-ihos/production/project-123/")
    key = stored.storage_uri.removeprefix("s3://private-ihos/")
    assert client.objects[("private-ihos", key)][0] == b"private drawing content"
    cached = provider.resolve_path(stored.storage_uri)
    cached.unlink()
    restored = provider.resolve_path(stored.storage_uri)
    assert restored.read_bytes() == b"private drawing content"
    provider.readiness_check()
    assert client.head_bucket_calls == ["private-ihos"]


def test_s3_provider_rejects_uri_outside_configured_bucket(tmp_path: Path) -> None:
    provider = S3FileStorageProvider(
        bucket="private-ihos",
        cache_root=tmp_path,
        client=FakeS3Client(),
    )

    with pytest.raises(HTTPException, match="Invalid object storage URI"):
        provider.resolve_path("s3://other-bucket/iron-house-os/project/file.pdf")


def test_s3_provider_rejects_download_with_wrong_object_checksum(tmp_path: Path) -> None:
    client = FakeS3Client()
    client.objects[("private-ihos", "iron-house-os/project/file.pdf")] = (
        b"tampered",
        {"Metadata": {"sha256": "0" * 64}},
    )
    provider = S3FileStorageProvider(
        bucket="private-ihos",
        cache_root=tmp_path,
        client=client,
    )

    with pytest.raises(HTTPException, match="failed its integrity check") as exc_info:
        provider.resolve_path("s3://private-ihos/iron-house-os/project/file.pdf")
    assert exc_info.value.status_code == 409


def test_build_storage_provider_supports_s3_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = FakeS3Client()
    monkeypatch.setenv("IHOS_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("IHOS_STORAGE_S3_BUCKET", "private-ihos")
    monkeypatch.setenv("IHOS_STORAGE_S3_PREFIX", "production")
    monkeypatch.setenv("IHOS_STORAGE_CACHE_ROOT", str(tmp_path))
    monkeypatch.setattr(file_storage.boto3, "client", lambda *args, **kwargs: client)

    provider = build_storage_provider()

    assert isinstance(provider, S3FileStorageProvider)
    assert provider.bucket == "private-ihos"
    assert provider.prefix == "production"
