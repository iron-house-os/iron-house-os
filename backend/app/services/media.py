import json
from uuid import UUID

from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.document import Document
from app.models.equipment import Equipment
from app.models.field_operations import FieldRecord, VehicleLog
from app.models.finance import FinancialEntry, StartupExpense
from app.models.media import MediaAsset, MediaRecordLink, MediaVersion
from app.models.project import Project
from app.schemas.media import (
    MediaAction,
    MediaAssetRead,
    MediaCategory,
    MediaLinkCreate,
    MediaMetadataUpdate,
    MediaOperation,
    MediaVersionRead,
)
from app.services import documents
from app.services.auth import AuthenticatedUser
from app.services.media_access import MANAGEMENT_ROLES, can_access_asset


CONTROLLED_CATEGORIES = {
    MediaCategory.flha.value,
    MediaCategory.incident.value,
    MediaCategory.expense.value,
    MediaCategory.receipt.value,
}
RECORD_MODELS = {
    "field_record": FieldRecord,
    "vehicle_log": VehicleLog,
    "equipment": Equipment,
    "financial_entry": FinancialEntry,
    "startup_expense": StartupExpense,
    "document": Document,
    "project": Project,
}
PROJECT_SCOPED_RECORD_TYPES = {
    "field_record",
    "vehicle_log",
    "financial_entry",
    "document",
    "project",
}


def _require_asset(db: Session, asset_id: UUID, user: AuthenticatedUser) -> MediaAsset:
    asset = db.get(MediaAsset, asset_id)
    if asset is None or not can_access_asset(asset, user):
        raise AppError("Photo asset not found", status_code=404)
    return asset


def _require_editor(asset: MediaAsset, user: AuthenticatedUser) -> None:
    if user.role in {"admin", "operations_manager", "estimator"}:
        return
    if user.role == "viewer" and asset.created_by_id == user.id:
        return
    raise AppError("You do not have permission to change this photo.", status_code=403)


def _record_project_id(record_type: str, record: object) -> UUID | None:
    if record_type == "project":
        return record.id
    return getattr(record, "project_id", None)


def _require_link_target(db: Session, payload: MediaLinkCreate) -> object:
    model = RECORD_MODELS.get(payload.record_type)
    if model is None:
        raise AppError("Unsupported photo record link.", status_code=422)
    record = db.get(model, payload.record_id)
    if record is None:
        raise AppError("Linked record not found.", status_code=404)
    return record


def _validate_record_project(asset: MediaAsset, record_type: str, record: object) -> None:
    if record_type not in PROJECT_SCOPED_RECORD_TYPES:
        return
    if _record_project_id(record_type, record) != asset.project_id:
        raise AppError("Photo and linked record must belong to the same project.", status_code=422)


def _validate_existing_link_projects(db: Session, asset: MediaAsset) -> None:
    links = db.scalars(select(MediaRecordLink).where(MediaRecordLink.asset_id == asset.id)).all()
    for link in links:
        model = RECORD_MODELS.get(link.record_type)
        record = db.get(model, link.record_id) if model is not None else None
        if record is None:
            raise AppError("Existing photo record link is no longer valid.", status_code=409)
        _validate_record_project(asset, link.record_type, record)


def _validate_amendment(asset: MediaAsset, action: MediaAction, reason: str | None) -> None:
    if asset.controlled and action in {MediaAction.replacement, MediaAction.restore} and not (reason or "").strip():
        raise AppError(
            "A reason is required to amend controlled safety or financial evidence.",
            status_code=422,
        )


def _parse_operations(raw: str | None) -> list[MediaOperation]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError("Photo operations must be valid JSON.", status_code=422) from exc
    if not isinstance(payload, list):
        raise AppError("Photo operations must be a list.", status_code=422)
    try:
        return [MediaOperation.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise AppError("Photo operations contain invalid values.", status_code=422) from exc


async def create_assets(
    db: Session,
    files: list[UploadFile],
    *,
    user: AuthenticatedUser,
    project_id: UUID | None,
    caption: str | None,
    captured_date,
    location: str | None,
    category: MediaCategory,
) -> list[MediaAssetRead]:
    if not files:
        raise AppError("Choose at least one photo.", status_code=422)
    if project_id and db.get(Project, project_id) is None:
        raise AppError("Project not found.", status_code=404)
    for file in files:
        if not (file.content_type or "").lower().startswith("image/"):
            raise AppError("Shared media accepts image files only.", status_code=422)
    results: list[MediaAssetRead] = []
    for file in files:
        upload = await documents.upload_document(
            db,
            user=user,
            file=file,
            title=caption,
            category="photo",
            project_id=project_id,
            description=caption,
        )
        asset = MediaAsset(
            original_document_id=upload.document.id,
            project_id=project_id,
            caption=caption,
            captured_date=captured_date,
            location=location,
            category=category.value,
            controlled=category.value in CONTROLLED_CATEGORIES,
            created_by_id=user.id,
            created_by_email=user.email,
        )
        db.add(asset)
        db.flush()
        version = MediaVersion(
            asset_id=asset.id,
            document_id=upload.document.id,
            version_number=1,
            action=MediaAction.original.value,
            editor_id=user.id,
            editor_email=user.email,
            operations=[],
            change_summary="Original upload retained as immutable evidence.",
        )
        db.add(version)
        db.flush()
        asset.current_version_id = version.id
        db.commit()
        results.append(get_asset(db, asset.id, user))
    return results


def register_document(
    db: Session,
    document_id: UUID,
    *,
    user: AuthenticatedUser,
    category: MediaCategory = MediaCategory.job_photo,
) -> MediaAssetRead:
    existing = db.scalar(select(MediaAsset).where(MediaAsset.original_document_id == document_id))
    if existing is not None:
        return get_asset(db, existing.id, user)
    document = db.get(Document, document_id)
    if document is None or document.category != "photo" or not document.storage_uri:
        raise AppError("Only stored photo documents can become media evidence.", status_code=422)
    asset = MediaAsset(
        original_document_id=document.id, project_id=document.project_id, caption=document.description or document.title,
        category=category.value, controlled=category.value in CONTROLLED_CATEGORIES,
        created_by_id=user.id, created_by_email=user.email,
    )
    db.add(asset)
    db.flush()
    version = MediaVersion(
        asset_id=asset.id, document_id=document.id, version_number=1, action=MediaAction.original.value,
        editor_id=user.id, editor_email=user.email, operations=[],
        change_summary="Original upload retained as immutable evidence.",
    )
    db.add(version)
    db.flush()
    asset.current_version_id = version.id
    db.commit()
    return get_asset(db, asset.id, user)


def list_assets(
    db: Session,
    user: AuthenticatedUser,
    *,
    project_id: UUID | None = None,
    record_type: str | None = None,
    record_id: UUID | None = None,
    document_ids: list[UUID] | None = None,
) -> list[MediaAssetRead]:
    statement = select(MediaAsset).order_by(MediaAsset.created_at.desc())
    if user.role not in MANAGEMENT_ROLES:
        statement = statement.where(MediaAsset.created_by_id == user.id)
    if project_id:
        statement = statement.where(MediaAsset.project_id == project_id)
    if document_ids:
        statement = statement.where(MediaAsset.original_document_id.in_(document_ids))
    if record_type or record_id:
        if not record_type or not record_id:
            raise AppError("record_type and record_id must be supplied together.", status_code=422)
        statement = statement.join(MediaRecordLink).where(
            MediaRecordLink.record_type == record_type,
            MediaRecordLink.record_id == record_id,
        )
    return [_to_schema(db, asset, user) for asset in db.scalars(statement).all()]


def get_asset(db: Session, asset_id: UUID, user: AuthenticatedUser) -> MediaAssetRead:
    return _to_schema(db, _require_asset(db, asset_id, user), user)


def link_asset(
    db: Session,
    asset_id: UUID,
    payload: MediaLinkCreate,
    user: AuthenticatedUser,
) -> MediaAssetRead:
    asset = _require_asset(db, asset_id, user)
    _require_editor(asset, user)
    record = _require_link_target(db, payload)
    _validate_record_project(asset, payload.record_type, record)
    exists = db.scalar(
        select(MediaRecordLink).where(
            MediaRecordLink.asset_id == asset.id,
            MediaRecordLink.record_type == payload.record_type,
            MediaRecordLink.record_id == payload.record_id,
        )
    )
    if exists is None:
        db.add(MediaRecordLink(asset_id=asset.id, **payload.model_dump()))
        db.commit()
    return get_asset(db, asset.id, user)


async def create_version(
    db: Session,
    asset_id: UUID,
    file: UploadFile,
    *,
    user: AuthenticatedUser,
    action: MediaAction,
    operations_json: str | None,
    change_summary: str | None,
    amendment_reason: str | None,
) -> MediaAssetRead:
    asset = _require_asset(db, asset_id, user)
    _require_editor(asset, user)
    if action not in {MediaAction.edit, MediaAction.replacement}:
        raise AppError("Only edit or replacement versions can upload a file.", status_code=422)
    _validate_amendment(asset, action, amendment_reason)
    operations = _parse_operations(operations_json)
    if action == MediaAction.edit and not operations:
        raise AppError("An edited version must describe at least one operation.", status_code=422)
    if not (file.content_type or "").lower().startswith("image/"):
        raise AppError("Photo versions must be image files.", status_code=422)
    current = db.get(MediaVersion, asset.current_version_id)
    next_version = _next_version_number(db, asset.id)
    upload = await documents.upload_document(
        db,
        user=user,
        file=file,
        title=asset.caption,
        category="photo",
        project_id=asset.project_id,
        description=change_summary,
        revision=str(next_version),
    )
    version = MediaVersion(
        asset_id=asset.id,
        parent_version_id=current.id if current else None,
        document_id=upload.document.id,
        version_number=next_version,
        action=action.value,
        editor_id=user.id,
        editor_email=user.email,
        operations=[item.model_dump(mode="json") for item in operations],
        change_summary=change_summary,
        amendment_reason=amendment_reason,
    )
    db.add(version)
    db.flush()
    asset.current_version_id = version.id
    db.commit()
    return get_asset(db, asset.id, user)


def restore_version(
    db: Session,
    asset_id: UUID,
    version_id: UUID,
    *,
    user: AuthenticatedUser,
    amendment_reason: str | None,
) -> MediaAssetRead:
    asset = _require_asset(db, asset_id, user)
    _require_editor(asset, user)
    _validate_amendment(asset, MediaAction.restore, amendment_reason)
    target = db.get(MediaVersion, version_id)
    if target is None or target.asset_id != asset.id:
        raise AppError("Photo version not found.", status_code=404)
    current = db.get(MediaVersion, asset.current_version_id)
    restored = MediaVersion(
        asset_id=asset.id,
        parent_version_id=current.id if current else None,
        document_id=target.document_id,
        version_number=_next_version_number(db, asset.id),
        action=MediaAction.restore.value,
        editor_id=user.id,
        editor_email=user.email,
        operations=[],
        change_summary=f"Restored version {target.version_number}.",
        amendment_reason=amendment_reason,
    )
    db.add(restored)
    db.flush()
    asset.current_version_id = restored.id
    db.commit()
    return get_asset(db, asset.id, user)


def update_metadata(
    db: Session,
    asset_id: UUID,
    payload: MediaMetadataUpdate,
    user: AuthenticatedUser,
) -> MediaAssetRead:
    asset = _require_asset(db, asset_id, user)
    _require_editor(asset, user)
    changes = payload.model_dump(exclude_unset=True)
    if user.role not in {"admin", "operations_manager"} and ({"location", "project_id"} & changes.keys()):
        raise AppError("Only management can change restricted location or project metadata.", status_code=403)
    if "project_id" in changes and changes["project_id"] is not None:
        if db.get(Project, changes["project_id"]) is None:
            raise AppError("Project not found.", status_code=404)
    if "category" in changes and changes["category"] is not None:
        changes["category"] = changes["category"].value
    for key, value in changes.items():
        setattr(asset, key, value)
    if "project_id" in changes:
        _validate_existing_link_projects(db, asset)
    if asset.category in CONTROLLED_CATEGORIES:
        asset.controlled = True
    current = db.get(MediaVersion, asset.current_version_id)
    version = MediaVersion(
        asset_id=asset.id,
        parent_version_id=current.id if current else None,
        document_id=current.document_id,
        version_number=_next_version_number(db, asset.id),
        action=MediaAction.edit.value,
        editor_id=user.id,
        editor_email=user.email,
        operations=[],
        change_summary="Metadata updated: " + ", ".join(sorted(changes)),
    )
    db.add(version)
    db.flush()
    asset.current_version_id = version.id
    db.commit()
    return get_asset(db, asset.id, user)


def version_file_document(
    db: Session,
    asset_id: UUID,
    user: AuthenticatedUser,
    version_id: UUID | None = None,
) -> Document:
    asset = _require_asset(db, asset_id, user)
    selected_id = version_id or asset.current_version_id
    version = db.get(MediaVersion, selected_id)
    if version is None or version.asset_id != asset.id:
        raise AppError("Photo version not found.", status_code=404)
    document = db.get(Document, version.document_id)
    if document is None:
        raise AppError("Photo file not found.", status_code=404)
    return document


def _next_version_number(db: Session, asset_id: UUID) -> int:
    return int(db.scalar(select(func.max(MediaVersion.version_number)).where(MediaVersion.asset_id == asset_id)) or 0) + 1


def _to_schema(db: Session, asset: MediaAsset, user: AuthenticatedUser) -> MediaAssetRead:
    versions = db.scalars(
        select(MediaVersion).where(MediaVersion.asset_id == asset.id).order_by(MediaVersion.version_number.desc())
    ).all()
    links = db.scalars(
        select(MediaRecordLink).where(MediaRecordLink.asset_id == asset.id).order_by(MediaRecordLink.created_at)
    ).all()
    return MediaAssetRead(
        id=asset.id,
        original_document_id=asset.original_document_id,
        current_version_id=asset.current_version_id,
        project_id=asset.project_id,
        caption=asset.caption,
        captured_date=asset.captured_date,
        location=asset.location if user.role in {"admin", "operations_manager"} else None,
        category=MediaCategory(asset.category),
        controlled=asset.controlled,
        created_by_email=asset.created_by_email,
        versions=[
            MediaVersionRead(
                id=item.id,
                asset_id=item.asset_id,
                parent_version_id=item.parent_version_id,
                document_id=item.document_id,
                version_number=item.version_number,
                action=MediaAction(item.action),
                editor_id=item.editor_id,
                editor_email=item.editor_email,
                operations=[MediaOperation.model_validate(operation) for operation in item.operations],
                change_summary=item.change_summary,
                amendment_reason=item.amendment_reason,
                created_at=item.created_at,
            )
            for item in versions
        ],
        links=[MediaLinkCreate(record_type=item.record_type, record_id=item.record_id) for item in links],
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )
