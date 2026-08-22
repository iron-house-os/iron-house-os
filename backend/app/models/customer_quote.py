from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CustomerQuote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_quotes"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    quote_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(320))
    customer_phone: Mapped[str | None] = mapped_column(String(80))
    site_address: Mapped[str | None] = mapped_column(String(500))
    scope_summary: Mapped[str] = mapped_column(Text, nullable=False)
    line_items_json: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    assumptions_json: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    exclusions_json: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    gst: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", index=True)
    record_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(320), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issue_status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", index=True)
    approved_revision: Mapped[int | None] = mapped_column(Integer)
    approved_snapshot_json: Mapped[dict | None] = mapped_column(JSONType)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(320))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_by: Mapped[str | None] = mapped_column(String(320))
    issuance_method: Mapped[str | None] = mapped_column(String(80))
    issuance_reference: Mapped[str | None] = mapped_column(String(500))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by: Mapped[str | None] = mapped_column(String(320))
    acceptance_reference: Mapped[str | None] = mapped_column(String(500))
    acceptance_note: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
