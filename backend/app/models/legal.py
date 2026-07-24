from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LegalMatter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "legal_matters"

    owner_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    matter_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    project_name: Mapped[str | None] = mapped_column(String(200))
    counterparty: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="unassessed", index=True)
    confidentiality: Mapped[str] = mapped_column(String(40), nullable=False, default="standard")
    jurisdiction: Mapped[str] = mapped_column(String(80), nullable=False, default="British Columbia, Canada")
    assigned_specialists: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LegalAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "legal_analyses"

    matter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("legal_matters.id"), nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    specialist_keys: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    draft_text: Mapped[str | None] = mapped_column(Text)
    issues: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    recommendations: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    questions_for_counsel: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    source_ids: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)


class LegalDeadline(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "legal_deadlines"

    matter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("legal_matters.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_basis: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate", index=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_by: Mapped[str | None] = mapped_column(String(255))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_reference: Mapped[str | None] = mapped_column(String(1000))


class LegalAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "legal_audit_events"

    matter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("legal_matters.id"), nullable=True, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
