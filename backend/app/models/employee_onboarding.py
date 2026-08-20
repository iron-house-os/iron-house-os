from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class EmployeeOnboarding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employee_onboardings"

    legal_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    legal_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(String(100))
    personal_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    mobile_phone: Mapped[str | None] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    position: Mapped[str] = mapped_column(String(60), nullable=False)
    supervisor_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"))
    employment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    primary_location: Mapped[str | None] = mapped_column(String(150))
    onboarding_package: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    completion_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_items: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_items: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    encrypted_portal_data: Mapped[str | None] = mapped_column(Text)
    reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_accounts.id"))
    correction_note: Mapped[str | None] = mapped_column(Text)
    invitation_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    invitation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invitation_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invitation_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), unique=True)


class EmployeeOnboardingAudit(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "employee_onboarding_audits"

    onboarding_id: Mapped[UUID] = mapped_column(ForeignKey("employee_onboardings.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkerOrientation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "worker_orientations"

    onboarding_id: Mapped[UUID] = mapped_column(ForeignKey("employee_onboardings.id"), index=True, nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    site_name: Mapped[str | None] = mapped_column(String(255))
    trigger: Mapped[str] = mapped_column(String(40), nullable=False)
    orientation_date: Mapped[date] = mapped_column(Date, nullable=False)
    instructor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    instructor_email: Mapped[str | None] = mapped_column(String(255))
    supervisor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    supervisor_email: Mapped[str | None] = mapped_column(String(255))
    document_version: Mapped[str] = mapped_column(String(80), nullable=False)
    topics: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    competency_result: Mapped[str] = mapped_column(String(30), nullable=False)
    ppe_verified: Mapped[bool] = mapped_column(nullable=False)
    qualifications_verified: Mapped[bool] = mapped_column(nullable=False)
    worker_acknowledged: Mapped[bool] = mapped_column(nullable=False)
    worker_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supporting_document_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
