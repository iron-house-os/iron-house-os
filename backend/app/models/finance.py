from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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


class CompanyCard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Authorized card directory. Full account numbers are deliberately not modelled."""

    __tablename__ = "company_cards"
    __table_args__ = (UniqueConstraint("brand", "last_four", "holder_email"),)

    brand: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    last_four: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    holder_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(120))
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class Receipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipts"

    status: Mapped[str] = mapped_column(String(40), default="draft_extraction", nullable=False, index=True)
    submitter_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    submitter_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    media_asset_ids: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vendor_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"), index=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255), index=True)
    vendor_address: Mapped[str | None] = mapped_column(String(500))
    reference: Mapped[str | None] = mapped_column(String(160), index=True)
    receipt_date: Mapped[date | None] = mapped_column(Date, index=True)
    receipt_time: Mapped[str | None] = mapped_column(String(16))
    currency: Mapped[str] = mapped_column(String(3), default="CAD", nullable=False)
    subtotal: Mapped[float | None] = mapped_column(Numeric(14, 2))
    discounts: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    gst: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    pst: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    other_tax: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    tip: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    payment_method: Mapped[str | None] = mapped_column(String(40))
    card_brand: Mapped[str | None] = mapped_column(String(40))
    card_last_four: Mapped[str | None] = mapped_column(String(4))
    company_card_id: Mapped[UUID | None] = mapped_column(ForeignKey("company_cards.id"), index=True)
    employee_email: Mapped[str | None] = mapped_column(String(255), index=True)
    treatment: Mapped[str] = mapped_column(String(40), default="needs_review", nullable=False)
    confidence_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    source_regions_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    flags_json: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    duplicate_of_id: Mapped[UUID | None] = mapped_column(ForeignKey("receipts.id"), index=True)
    approved_by: Mapped[str | None] = mapped_column(String(255))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exported_by: Mapped[str | None] = mapped_column(String(255))
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by: Mapped[str | None] = mapped_column(String(255))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ReceiptLineItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipt_line_items"
    __table_args__ = (UniqueConstraint("receipt_id", "position"),)

    receipt_id: Mapped[UUID] = mapped_column(ForeignKey("receipts.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[str | None] = mapped_column(String(255), index=True)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    tax: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="uncategorized", nullable=False, index=True)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    equipment_id: Mapped[UUID | None] = mapped_column(ForeignKey("equipment.id"), index=True)
    cost_code: Mapped[str | None] = mapped_column(String(32), index=True)
    overhead_category: Mapped[str | None] = mapped_column(String(80), index=True)
    treatment: Mapped[str] = mapped_column(String(40), default="needs_review", nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    source_region_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    flags_json: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)


class ReceiptAlias(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipt_aliases"
    __table_args__ = (UniqueConstraint("vendor_id", "raw_value"),)

    vendor_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)
    raw_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    cost_code: Mapped[str | None] = mapped_column(String(32))
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False)


class ReceiptAuditEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipt_audit_events"

    receipt_id: Mapped[UUID] = mapped_column(ForeignKey("receipts.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str | None] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(Text)
    changes_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
