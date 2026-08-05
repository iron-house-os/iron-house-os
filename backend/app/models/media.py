from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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


class BackupIntake(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_intakes"
    __table_args__ = (
        UniqueConstraint("media_asset_id"),
        UniqueConstraint("uploader_id", "media_sha256"),
        UniqueConstraint("destination_type", "destination_record_id"),
    )

    media_asset_id: Mapped[UUID] = mapped_column(ForeignKey("media_assets.id"), nullable=False, index=True)
    media_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploader_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    uploader_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    uploader_role: Mapped[str] = mapped_column(String(80), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    project_hint: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    detected_type: Mapped[str | None] = mapped_column(String(40), index=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    destination_type: Mapped[str | None] = mapped_column(String(80), index=True)
    destination_record_id: Mapped[UUID | None] = mapped_column(index=True)
    error: Mapped[str | None] = mapped_column(Text)
    sensitive_quarantine: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    classifier: Mapped[str | None] = mapped_column(String(120))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    routed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BackupIntakeAuditEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_intake_audit_events"

    intake_id: Mapped[UUID] = mapped_column(ForeignKey("backup_intakes.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str | None] = mapped_column(String(40))
    detail_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
