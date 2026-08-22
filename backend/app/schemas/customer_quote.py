from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerQuoteStatus(StrEnum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"


class CustomerQuoteIssueStatus(StrEnum):
    draft = "draft"
    ready_for_review = "ready_for_review"
    approved_for_issue = "approved_for_issue"
    issued = "issued"


class CustomerQuoteLineItem(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, decimal_places=3, max_digits=14)
    unit: str = Field(default="LS", min_length=1, max_length=40)
    unit_price: Decimal = Field(ge=0, decimal_places=2, max_digits=14)


class CustomerQuoteCreate(BaseModel):
    project_id: UUID | None = None
    project_name: str = Field(min_length=1, max_length=255)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: str | None = Field(default=None, max_length=320)
    customer_phone: str | None = Field(default=None, max_length=80)
    site_address: str | None = Field(default=None, max_length=500)
    scope_summary: str = Field(min_length=1, max_length=10_000)
    line_items: list[CustomerQuoteLineItem] = Field(min_length=1, max_length=250)
    assumptions: list[str] = Field(default_factory=list, max_length=100)
    exclusions: list[str] = Field(default_factory=list, max_length=100)
    gst_rate: Decimal = Field(default=Decimal("5.00"), ge=0, le=100, decimal_places=4)
    quote_date: date = Field(default_factory=date.today)
    valid_until: date | None = None
    notes: str | None = Field(default=None, max_length=10_000)


class CustomerQuoteUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    customer_name: str | None = Field(default=None, min_length=1, max_length=255)
    customer_email: str | None = Field(default=None, max_length=320)
    customer_phone: str | None = Field(default=None, max_length=80)
    site_address: str | None = Field(default=None, max_length=500)
    scope_summary: str | None = Field(default=None, min_length=1, max_length=10_000)
    line_items: list[CustomerQuoteLineItem] | None = Field(default=None, min_length=1, max_length=250)
    assumptions: list[str] | None = Field(default=None, max_length=100)
    exclusions: list[str] | None = Field(default=None, max_length=100)
    gst_rate: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=4)
    quote_date: date | None = None
    valid_until: date | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("quote_date", mode="before")
    @classmethod
    def reject_null_quote_date(cls, value: object) -> object:
        if value is None:
            raise ValueError("quote_date cannot be null")
        return value


class CustomerQuoteStatusUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    status: CustomerQuoteStatus
    note: str | None = Field(default=None, max_length=10_000)


class CustomerQuoteAccept(BaseModel):
    expected_revision: int = Field(ge=1)
    acceptance_reference: str = Field(min_length=1, max_length=500)
    acceptance_note: str | None = Field(default=None, max_length=10_000)


class CustomerQuoteIssueUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    status: CustomerQuoteIssueStatus
    issuance_method: str | None = Field(default=None, max_length=80)
    issuance_reference: str | None = Field(default=None, max_length=500)


class CustomerQuoteRead(BaseModel):
    id: UUID
    project_id: UUID
    project_name: str
    quote_number: str
    customer_name: str
    customer_email: str | None
    customer_phone: str | None
    site_address: str | None
    scope_summary: str
    line_items: list[dict]
    assumptions: list[str]
    exclusions: list[str]
    subtotal: Decimal
    gst_rate: Decimal
    gst: Decimal
    total: Decimal
    quote_date: date
    valid_until: date | None
    status: CustomerQuoteStatus
    record_revision: int
    notes: str | None
    created_by: str
    sent_at: datetime | None
    issue_status: CustomerQuoteIssueStatus
    approved_revision: int | None
    approved_at: datetime | None
    approved_by: str | None
    issued_at: datetime | None
    issued_by: str | None
    issuance_method: str | None
    issuance_reference: str | None
    accepted_at: datetime | None
    accepted_by: str | None
    acceptance_reference: str | None
    acceptance_note: str | None
    closed_at: datetime | None
    job_number: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerQuoteList(BaseModel):
    items: list[CustomerQuoteRead]
    total: int
