from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FinancialEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_entries"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    cost_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    reference: Mapped[str | None] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    source_id: Mapped[UUID | None]
    status: Mapped[str] = mapped_column(String(40), default="posted", nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class StartupExpense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "startup_expenses"

    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    reference: Mapped[str | None] = mapped_column(String(160), index=True)
    source_email: Mapped[str | None] = mapped_column(String(255))
    funding_source: Mapped[str] = mapped_column(String(40), default="owner_loan", nullable=False, index=True)
    owner_name: Mapped[str | None] = mapped_column(String(255))
    tax_treatment: Mapped[str] = mapped_column(String(40), default="needs_review", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="review", nullable=False, index=True)
    receipt_metadata: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
