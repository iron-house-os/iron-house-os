from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile, status

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".dwg",
    ".dxf",
    ".xlsx",
    ".xls",
    ".docx",
    ".doc",
    ".zip",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
DEFAULT_STORAGE_ROOT = Path("/app/data/uploads")


@dataclass(frozen=True)
class StoredFile:
    storage_uri: str
    original_filename: str
    safe_filename: str
    extension: str
    content_type: str | None
    size_bytes: int
    sha256_hash: str


class FileStorageProvider(Protocol):
    """Storage contract used by document services."""

    async def store_upload(self, file: UploadFile, project_id: str | None = None) -> StoredFile: ...

    def resolve_path(self, storage_uri: str) -> Path: ...

    def readiness_check(self) -> None: ...


def _upload_identity(file: UploadFile) -> tuple[str, str, str]:
    original_filename = file.filename or "upload"
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {extension or 'none'}",
        )
    return original_filename, extension, f"{uuid4().hex}{extension}"


def _storage_namespace(project_id: str | None) -> str:
    namespace = project_id or "unassigned"
    if not namespace.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project storage namespace",
        )
    return namespace


def _path_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


async def _write_upload(file: UploadFile, target_path: Path) -> tuple[int, str]:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256()
    size = 0
    with target_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                target_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File exceeds upload limit",
                )
            digest.update(chunk)
            output.write(chunk)
    return size, digest.hexdigest()


class LocalFileStorageProvider:
    def __init__(self, root: Path = DEFAULT_STORAGE_ROOT) -> None:
        self.root = root

    async def store_upload(self, file: UploadFile, project_id: str | None = None) -> StoredFile:
        original_filename, extension, safe_filename = _upload_identity(file)
        target_dir = self.root / _storage_namespace(project_id)
        target_path = target_dir / safe_filename
        size, digest = await _write_upload(file, target_path)

        return StoredFile(
            storage_uri=str(target_path),
            original_filename=original_filename,
            safe_filename=safe_filename,
            extension=extension,
            content_type=file.content_type,
            size_bytes=size,
            sha256_hash=digest,
        )

    def resolve_path(self, storage_uri: str) -> Path:
        path = Path(storage_uri)
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage path",
            ) from exc
        if not path.exists() or not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored file not found",
            )
        return path

    def readiness_check(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(prefix=".readiness-", dir=self.root):
            pass


class S3FileStorageProvider:
    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "iron-house-os",
        cache_root: Path = Path("/app/data/object-cache"),
        region: str | None = None,
        endpoint_url: str | None = None,
        client: Any | None = None,
    ) -> None:
        if not bucket.strip():
            raise RuntimeError("IHOS_STORAGE_S3_BUCKET is required for the S3 backend.")
        normalized_prefix = prefix.strip("/")
        prefix_parts = normalized_prefix.split("/")
        if (
            not normalized_prefix
            or any(part in {"", ".", ".."} for part in prefix_parts)
            or any(not part.replace("-", "").replace("_", "").replace(".", "").isalnum() for part in prefix_parts)
        ):
            raise RuntimeError("IHOS_STORAGE_S3_PREFIX must be a safe non-empty key prefix.")
        self.bucket = bucket.strip()
        self.prefix = normalized_prefix
        self.cache_root = cache_root
        self.client = client or boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
        )

    def _key(self, project_id: str | None, safe_filename: str) -> str:
        namespace = _storage_namespace(project_id)
        return f"{self.prefix}/{namespace}/{safe_filename}"

    def _cache_path(self, key: str) -> Path:
        path = self.cache_root / key
        try:
            path.resolve().relative_to(self.cache_root.resolve())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid object storage key",
            ) from exc
        return path

    async def store_upload(self, file: UploadFile, project_id: str | None = None) -> StoredFile:
        original_filename, extension, safe_filename = _upload_identity(file)
        key = self._key(project_id, safe_filename)
        cache_path = self._cache_path(key)
        size, digest = await _write_upload(file, cache_path)
        try:
            self.client.upload_file(
                str(cache_path),
                self.bucket,
                key,
                ExtraArgs={
                    "ContentType": file.content_type or "application/octet-stream",
                    "Metadata": {"sha256": digest},
                },
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            cache_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Object storage is unavailable",
            ) from exc
        return StoredFile(
            storage_uri=f"s3://{self.bucket}/{key}",
            original_filename=original_filename,
            safe_filename=safe_filename,
            extension=extension,
            content_type=file.content_type,
            size_bytes=size,
            sha256_hash=digest,
        )

    def resolve_path(self, storage_uri: str) -> Path:
        parsed = urlparse(storage_uri)
        key = parsed.path.lstrip("/")
        if parsed.scheme != "s3" or parsed.netloc != self.bucket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid object storage URI",
            )
        if not key.startswith(f"{self.prefix}/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Object storage URI is outside the configured prefix",
            )
        cache_path = self._cache_path(key)
        if not cache_path.is_file():
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.client.download_file(self.bucket, key, str(cache_path))
                metadata = self.client.head_object(Bucket=self.bucket, Key=key).get("Metadata", {})
            except (BotoCoreError, ClientError, OSError) as exc:
                cache_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Stored object not found",
                ) from exc
            expected_hash = metadata.get("sha256")
            if expected_hash and _path_digest(cache_path) != expected_hash:
                cache_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Stored object failed its integrity check",
                )
        return cache_path

    def readiness_check(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except (BotoCoreError, ClientError, OSError) as exc:
            raise RuntimeError("Object storage is unavailable.") from exc


def build_storage_provider() -> FileStorageProvider:
    backend = os.getenv("IHOS_STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        root = Path(os.getenv("IHOS_STORAGE_ROOT", str(DEFAULT_STORAGE_ROOT)))
        return LocalFileStorageProvider(root=root)
    if backend == "s3":
        return S3FileStorageProvider(
            bucket=os.getenv("IHOS_STORAGE_S3_BUCKET", ""),
            prefix=os.getenv("IHOS_STORAGE_S3_PREFIX", "iron-house-os"),
            cache_root=Path(os.getenv("IHOS_STORAGE_CACHE_ROOT", "/app/data/object-cache")),
            region=os.getenv("AWS_REGION") or None,
            endpoint_url=os.getenv("IHOS_STORAGE_S3_ENDPOINT_URL") or None,
        )
    raise RuntimeError(f"Unsupported IHOS_STORAGE_BACKEND: {backend}")


storage_provider: FileStorageProvider = build_storage_provider()


async def store_upload(file: UploadFile, project_id: str | None = None) -> StoredFile:
    """Compatibility wrapper for the configured storage provider."""

    return await storage_provider.store_upload(file, project_id)


def resolve_storage_path(storage_uri: str) -> Path:
    """Compatibility wrapper for the configured storage provider."""

    return storage_provider.resolve_path(storage_uri)
