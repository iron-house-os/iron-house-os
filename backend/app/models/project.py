from datetime import date
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_owner: Mapped[str | None] = mapped_column(String(255))
    municipality_name: Mapped[str | None] = mapped_column("municipality", String(255))
    project_number: Mapped[str | None] = mapped_column(String(80), unique=True)
    tender_number: Mapped[str | None] = mapped_column(String(120))
    tender_source: Mapped[str | None] = mapped_column(String(255))
    tender_closing_date: Mapped[date | None] = mapped_column(Date)
    bid_due_date: Mapped[date | None] = mapped_column(Date)
    estimated_construction_start: Mapped[date | None] = mapped_column(Date)
    estimated_construction_finish: Mapped[date | None] = mapped_column(Date)
    project_address: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    contract_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(80), default="opportunity")
    municipality_id: Mapped[UUID | None] = mapped_column(ForeignKey("municipalities.id"))
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    municipality_ref = relationship("Municipality", back_populates="projects")
    rfqs = relationship("RFQ", back_populates="project")
    rfq_packages = relationship("RFQPackage", back_populates="project")
    bids = relationship("Bid", back_populates="project")
    drawings = relationship("Drawing", back_populates="project")
    takeoffs = relationship("Takeoff", back_populates="project")
    supplier_links = relationship(
        "ProjectSupplier",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectSupplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_suppliers"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120))

    project = relationship("Project", back_populates="supplier_links")
    supplier = relationship("Supplier")
