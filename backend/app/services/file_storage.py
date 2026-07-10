from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
from typing import Protocol
from uuid import uuid4

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


class LocalFileStorageProvider:
    def __init__(self, root: Path = DEFAULT_STORAGE_ROOT) -> None:
        self.root = root

    async def store_upload(self, file: UploadFile, project_id: str | None = None) -> StoredFile:
        original_filename = file.filename or "upload"
        extension = Path(original_filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension: {extension or 'none'}",
            )

        target_dir = self.root / (project_id or "unassigned")
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{uuid4().hex}{extension}"
        target_path = target_dir / safe_filename

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

        return StoredFile(
            storage_uri=str(target_path),
            original_filename=original_filename,
            safe_filename=safe_filename,
            extension=extension,
            content_type=file.content_type,
            size_bytes=size,
            sha256_hash=digest.hexdigest(),
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


def build_storage_provider() -> FileStorageProvider:
    backend = os.getenv("IHOS_STORAGE_BACKEND", "local").strip().lower()
    if backend != "local":
        raise RuntimeError(f"Unsupported IHOS_STORAGE_BACKEND: {backend}")

    root = Path(os.getenv("IHOS_STORAGE_ROOT", str(DEFAULT_STORAGE_ROOT)))
    return LocalFileStorageProvider(root=root)


storage_provider: FileStorageProvider = build_storage_provider()


async def store_upload(file: UploadFile, project_id: str | None = None) -> StoredFile:
    """Compatibility wrapper for the configured storage provider."""

    return await storage_provider.store_upload(file, project_id)


def resolve_storage_path(storage_uri: str) -> Path:
    """Compatibility wrapper for the configured storage provider."""

    return storage_provider.resolve_path(storage_uri)
