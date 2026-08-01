from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_assets"

    original_document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, unique=True)
    current_version_id: Mapped[UUID | None]
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    caption: Mapped[str | None] = mapped_column(Text)
    captured_date: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(80), default="job_photo", nullable=False)
    controlled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(nullable=False)
    created_by_email: Mapped[str] = mapped_column(String(255), nullable=False)


class MediaVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_versions"
    __table_args__ = (UniqueConstraint("asset_id", "version_number"),)

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("media_assets.id"), nullable=False, index=True)
    parent_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_versions.id"))
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    editor_id: Mapped[UUID] = mapped_column(nullable=False)
    editor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    operations: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text)
    amendment_reason: Mapped[str | None] = mapped_column(Text)


class MediaRecordLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_record_links"
    __table_args__ = (UniqueConstraint("asset_id", "record_type", "record_id"),)

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("media_assets.id"), nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    record_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
