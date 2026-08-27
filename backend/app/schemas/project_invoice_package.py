from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.finance import CustomerInvoiceRead


class ProjectInvoiceSourceLineRead(BaseModel):
    id: UUID
    work_date: date
    source_line_key: str
    source_invoice_number: str | None
    description: str
    quantity: str
    unit: str
    billable_rate: str
    billable_amount: str


class ProjectInvoiceSourceGroupRead(BaseModel):
    source_import_key: str
    source_invoice_number: str | None
    source_drive_file_id: str | None
    source_invoice_date: date | None
    line_count: int
    subtotal: str
    ready: bool
    blockers: list[str]
    lines: list[ProjectInvoiceSourceLineRead]
    existing_invoice_id: UUID | None
    existing_invoice_number: str | None
    existing_invoice_status: str | None


class ProjectInvoicePackageReadiness(BaseModel):
    project_id: UUID
    project_number: str | None
    project_name: str
    project_status: str
    site_address: str | None
    customer_reference: str | None
    closeout_status: Literal["ready", "not_ready", "missing"]
    ready: bool
    blockers: list[str]
    groups: list[ProjectInvoiceSourceGroupRead]


class ProjectInvoicePackageCreate(BaseModel):
    source_import_key: str = Field(min_length=1, max_length=255)
    invoice_number: str = Field(min_length=1, max_length=80)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_address: str = Field(min_length=1, max_length=500)
    customer_phone: str | None = Field(default=None, max_length=40)
    invoice_date: date
    due_date: date
    terms: str = Field(default="Net 30", min_length=1, max_length=80)
    gst_rate: str = Field(default="5.00", min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectInvoicePackageCreate":
        if self.due_date < self.invoice_date:
            raise ValueError("Due date cannot precede invoice date.")
        return self


class ProjectInvoicePackageResult(BaseModel):
    invoice: CustomerInvoiceRead
    created: bool
    idempotent: bool
    generated_at: datetime
