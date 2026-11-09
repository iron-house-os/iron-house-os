from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Vehicle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"

    unit_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_driver_name: Mapped[str | None] = mapped_column(String(255))
    assigned_employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"))
    make: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    year: Mapped[int | None]
    vin: Mapped[str | None] = mapped_column(String(40), unique=True)
    licence_plate: Mapped[str | None] = mapped_column(String(40))
    current_km: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    next_service_km: Mapped[float | None] = mapped_column(Float)
    next_service_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class VehicleLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_logs"

    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"))
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"))
    log_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    odometer_km: Mapped[float | None] = mapped_column(Float)
    litres: Mapped[float | None] = mapped_column(Float)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    vendor: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[str | None] = mapped_column(Text)
    document_ids: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)


class EmployeeCertification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employee_certifications"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(255))
    certificate_number: Mapped[str | None] = mapped_column(String(120))
    issued_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id"))
    notes: Mapped[str | None] = mapped_column(Text)


class TimeEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "time_entries"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    cost_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    regular_hours: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    overtime_hours: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(40), default="employee", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="submitted", nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(String(255))


class FieldRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "field_records"

    record_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), index=True)
    equipment_id: Mapped[UUID | None] = mapped_column(ForeignKey("equipment.id"))
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"))
    cost_code: Mapped[str | None] = mapped_column(String(32), index=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="submitted", nullable=False)
    severity: Mapped[str] = mapped_column(String(40), default="none", nullable=False)
    details: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    document_ids: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    signatures: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    alert_recipients: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(String(255))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
