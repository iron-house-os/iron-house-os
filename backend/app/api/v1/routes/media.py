from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.media import (
    MediaAction,
    MediaAssetRead,
    MediaCategory,
    MediaLinkCreate,
    MediaMetadataUpdate,
    MediaRestoreRequest,
)
from app.services import media
from app.services.file_storage import resolve_storage_path

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=list[MediaAssetRead], status_code=status.HTTP_201_CREATED)
async def upload_photos(
    user: CurrentUser,
    db: DBSession,
    files: list[UploadFile] = File(...),
    project_id: UUID | None = Form(default=None),
    caption: str | None = Form(default=None),
    captured_date: date | None = Form(default=None),
    location: str | None = Form(default=None),
    category: MediaCategory = Form(default=MediaCategory.job_photo),
) -> list[MediaAssetRead]:
    return await media.create_assets(
        db,
        files,
        user=user,
        project_id=project_id,
        caption=caption,
        captured_date=captured_date,
        location=location,
        category=category,
    )


@router.get("", response_model=list[MediaAssetRead])
def list_photos(
    user: CurrentUser,
    db: DBSession,
    project_id: UUID | None = Query(default=None),
    record_type: str | None = Query(default=None),
    record_id: UUID | None = Query(default=None),
    document_ids: list[UUID] | None = Query(default=None),
) -> list[MediaAssetRead]:
    return media.list_assets(
        db,
        user,
        project_id=project_id,
        record_type=record_type,
        record_id=record_id,
        document_ids=document_ids,
    )


@router.get("/{asset_id}", response_model=MediaAssetRead)
def read_photo(asset_id: UUID, user: CurrentUser, db: DBSession) -> MediaAssetRead:
    return media.get_asset(db, asset_id, user)


@router.patch("/{asset_id}", response_model=MediaAssetRead)
def update_photo_metadata(
    asset_id: UUID,
    payload: MediaMetadataUpdate,
    user: CurrentUser,
    db: DBSession,
) -> MediaAssetRead:
    return media.update_metadata(db, asset_id, payload, user)


@router.post("/{asset_id}/links", response_model=MediaAssetRead)
def link_photo(
    asset_id: UUID,
    payload: MediaLinkCreate,
    user: CurrentUser,
    db: DBSession,
) -> MediaAssetRead:
    return media.link_asset(db, asset_id, payload, user)


@router.post("/{asset_id}/versions", response_model=MediaAssetRead)
async def add_photo_version(
    asset_id: UUID,
    user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
    action: MediaAction = Form(default=MediaAction.edit),
    operations: str | None = Form(default=None),
    change_summary: str | None = Form(default=None),
    amendment_reason: str | None = Form(default=None),
) -> MediaAssetRead:
    return await media.create_version(
        db,
        asset_id,
        file,
        user=user,
        action=action,
        operations_json=operations,
        change_summary=change_summary,
        amendment_reason=amendment_reason,
    )


@router.post("/{asset_id}/restore", response_model=MediaAssetRead)
def restore_photo_version(
    asset_id: UUID,
    payload: MediaRestoreRequest,
    user: CurrentUser,
    db: DBSession,
) -> MediaAssetRead:
    return media.restore_version(
        db,
        asset_id,
        payload.version_id,
        user=user,
        amendment_reason=payload.amendment_reason,
    )


@router.get("/{asset_id}/content")
def view_photo(
    asset_id: UUID,
    user: CurrentUser,
    db: DBSession,
    version_id: UUID | None = Query(default=None),
    download: bool = Query(default=False),
) -> FileResponse:
    document = media.version_file_document(db, asset_id, user, version_id)
    path = resolve_storage_path(document.storage_uri or "")
    metadata = document.metadata_json or {}
    return FileResponse(
        path,
        media_type=metadata.get("content_type") or "image/jpeg",
        filename=metadata.get("original_filename") if download else None,
        content_disposition_type="attachment" if download else "inline",
    )
