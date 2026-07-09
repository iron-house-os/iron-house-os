from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
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
STORAGE_ROOT = Path("/app/data/uploads")


@dataclass(frozen=True)
class StoredFile:
    storage_uri: str
    original_filename: str
    safe_filename: str
    extension: str
    content_type: str | None
    size_bytes: int
    sha256_hash: str


async def store_upload(file: UploadFile, project_id: str | None = None) -> StoredFile:
    original_filename = file.filename or "upload"
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {extension or 'none'}",
        )

    target_dir = STORAGE_ROOT / (project_id or "unassigned")
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


def resolve_storage_path(storage_uri: str) -> Path:
    path = Path(storage_uri)
    try:
        path.resolve().relative_to(STORAGE_ROOT.resolve())
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
