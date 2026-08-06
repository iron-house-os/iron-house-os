from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class BackupsIntake(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backups_intakes"

    media_id: Mapped[UUID] = mapped_column(ForeignKey("media_assets.id"), nullable=False, unique=True)
    media_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    uploader_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    uploader_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    uploader_role: Mapped[str] = mapped_column(String(80), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    project_hint: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    detected_type: Mapped[str | None] = mapped_column(String(40), index=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    classification_source: Mapped[str | None] = mapped_column(String(80))
    review_destination: Mapped[str | None] = mapped_column(String(80), index=True)
    routing_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    destination_type: Mapped[str | None] = mapped_column(String(80))
    destination_record_id: Mapped[UUID | None] = mapped_column(index=True)
    error: Mapped[str | None] = mapped_column(Text)
    sensitive_quarantine: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    routed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BackupsRoute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backups_routes"
    __table_args__ = (UniqueConstraint("media_hash", "detected_type"),)

    media_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    detected_type: Mapped[str] = mapped_column(String(40), nullable=False)
    destination_type: Mapped[str] = mapped_column(String(80), nullable=False)
    destination_record_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    created_by_intake_id: Mapped[UUID] = mapped_column(ForeignKey("backups_intakes.id"), nullable=False)


class BackupsAuditEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backups_audit_events"

    intake_id: Mapped[UUID] = mapped_column(ForeignKey("backups_intakes.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str | None] = mapped_column(String(40))
    details_json: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
