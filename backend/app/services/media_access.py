from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.media import MediaAsset, MediaRecordLink, MediaVersion
from app.services.auth import AuthenticatedUser


MANAGEMENT_ROLES = {"admin", "operations_manager"}


def can_access_asset(asset: MediaAsset, user: AuthenticatedUser) -> bool:
    # Project membership is not modelled yet. Until it is, ownership is the
    # safest non-disclosing project boundary for non-management principals.
    return user.role in MANAGEMENT_ROLES or asset.created_by_id == user.id


def media_assets_for_document(db: Session, document_id: UUID) -> list[MediaAsset]:
    """Return media owners for an original or any current/prior version document."""
    return list(
        db.scalars(
            select(MediaAsset)
            .outerjoin(MediaVersion, MediaVersion.asset_id == MediaAsset.id)
            .where(
                or_(
                    MediaAsset.original_document_id == document_id,
                    MediaVersion.document_id == document_id,
                )
            )
            .distinct()
        )
        .all()
    )


def can_access_document(db: Session, document_id: UUID, user: AuthenticatedUser) -> bool:
    assets = media_assets_for_document(db, document_id)
    linked_assets = list(
        db.scalars(
            select(MediaAsset)
            .join(MediaRecordLink, MediaRecordLink.asset_id == MediaAsset.id)
            .where(
                MediaRecordLink.record_type == "document",
                MediaRecordLink.record_id == document_id,
            )
        ).all()
    )
    assets.extend(asset for asset in linked_assets if asset.id not in {item.id for item in assets})
    return all(can_access_asset(asset, user) for asset in assets)


def require_document_access(db: Session, document_id: UUID, user: AuthenticatedUser) -> None:
    if not can_access_document(db, document_id, user):
        raise AppError("Document not found", status_code=404)
