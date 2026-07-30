from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RFQ(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfqs"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="draft")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope_summary: Mapped[str | None] = mapped_column(Text)
    package_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    project = relationship("Project", back_populates="rfqs")
    quotes = relationship("Quote", back_populates="rfq")


class Quote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quotes"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    rfq_id: Mapped[UUID | None] = mapped_column(ForeignKey("rfqs.id"))
    rfq_package_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rfq_packages.id"),
        index=True,
    )
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"))
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quote_reference: Mapped[str | None] = mapped_column(String(120))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    line_item_code: Mapped[str | None] = mapped_column(String(120))
    line_item_description: Mapped[str | None] = mapped_column(String(500))
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(80), default="material")
    status: Mapped[str] = mapped_column(String(80), default="requested")
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=True)
    qualification_notes: Mapped[list[str]] = mapped_column(JSONType, default=list)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    selection_reason: Mapped[str | None] = mapped_column(Text)
    exclusions: Mapped[list[str]] = mapped_column(JSONType, default=list)
    notes: Mapped[str | None] = mapped_column(Text)

    project = relationship("Project", back_populates="quotes")
    rfq = relationship("RFQ", back_populates="quotes")
    rfq_package = relationship("RFQPackage", back_populates="quotes")
    supplier = relationship("Supplier", back_populates="quotes")


class RFQPackage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfq_packages"

    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    project_name: Mapped[str | None] = mapped_column(String(255))
    scope_summary: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(80), default="draft")
    supplier_category_targets: Mapped[list[str]] = mapped_column(JSONType, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    project = relationship("Project", back_populates="rfq_packages")
    recipients = relationship(
        "RFQPackageSupplierRecipient",
        back_populates="rfq_package",
        cascade="all, delete-orphan",
    )
    documents = relationship(
        "RFQPackageDocument",
        back_populates="rfq_package",
        cascade="all, delete-orphan",
    )
    quotes = relationship("Quote", back_populates="rfq_package")


class RFQPackageSupplierRecipient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfq_package_supplier_recipients"

    rfq_package_id: Mapped[UUID] = mapped_column(ForeignKey("rfq_packages.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(120), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(80), default="selected")

    rfq_package = relationship("RFQPackage", back_populates="recipients")


class RFQPackageDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfq_package_documents"

    rfq_package_id: Mapped[UUID] = mapped_column(ForeignKey("rfq_packages.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(80), default="registered")
    storage_uri: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    rfq_package = relationship("RFQPackage", back_populates="documents")
