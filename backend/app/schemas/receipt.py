from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


ReceiptStatus = Literal["draft_extraction", "needs_review", "approved", "exported", "reconciled", "void"]
ReceiptCategory = Literal[
    "fuel", "tools", "ppe", "materials", "equipment_parts_service", "rentals",
    "meals_travel", "office_admin", "uncategorized",
]
ReceiptTreatment = Literal["company_card", "reimbursable", "company_paid", "needs_review"]


class SourceRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(ge=1)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class ReceiptLineItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=500)
    normalized_description: str | None = Field(default=None, max_length=255)
    quantity: float = Field(default=1, gt=0, le=100_000)
    unit_price: float = Field(ge=0, le=999_999_999)
    tax: float = Field(default=0, ge=0, le=999_999_999)
    line_total: float = Field(ge=0, le=999_999_999)
    category: ReceiptCategory = "uncategorized"
    project_id: UUID | None = None
    equipment_id: UUID | None = None
    cost_code: str | None = Field(default=None, max_length=32)
    overhead_category: Literal["general_overhead", "office_admin", "training", "business_development"] | None = None
    treatment: ReceiptTreatment = "needs_review"
    confidence: float = Field(default=0, ge=0, le=1)
    source_region: SourceRegion | None = None
    flags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("description", "normalized_description")
    @classmethod
    def reject_sensitive_line_text(cls, value: str | None) -> str | None:
        if value and _contains_pan(value):
            raise ValueError("Full payment card numbers are not accepted in receipt lines.")
        lowered = (value or "").lower()
        if any(term in lowered for term in ("social insurance number", "bank account", "medical record", "payroll account")):
            raise ValueError("Sensitive banking, payroll, medical, and SIN data are outside receipt intake.")
        return value


class ReceiptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    media_asset_ids: list[UUID] = Field(min_length=1, max_length=10)
    vendor_name: str | None = Field(default=None, max_length=255)
    vendor_address: str | None = Field(default=None, max_length=500)
    reference: str | None = Field(default=None, max_length=160)
    receipt_date: date | None = None
    receipt_time: str | None = Field(default=None, max_length=16)
    currency: str = Field(default="CAD", pattern=r"^[A-Z]{3}$")
    subtotal: float | None = Field(default=None, ge=0, le=999_999_999)
    discounts: float = Field(default=0, ge=0, le=999_999_999)
    gst: float = Field(default=0, ge=0, le=999_999_999)
    pst: float = Field(default=0, ge=0, le=999_999_999)
    other_tax: float = Field(default=0, ge=0, le=999_999_999)
    tip: float = Field(default=0, ge=0, le=999_999_999)
    total: float | None = Field(default=None, ge=0, le=999_999_999)
    payment_method: str | None = Field(default=None, max_length=40)
    card_brand: str | None = Field(default=None, max_length=40)
    card_last_four: str | None = Field(default=None, pattern=r"^\d{4}$")
    employee_email: str | None = Field(default=None, max_length=255)
    treatment: ReceiptTreatment = "needs_review"
    confidence: dict[str, float] = Field(default_factory=dict)
    source_regions: dict[str, SourceRegion] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list, max_length=30)
    line_items: list[ReceiptLineItemInput] = Field(default_factory=list, max_length=200)

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value: dict[str, float]) -> dict[str, float]:
        if any(score < 0 or score > 1 for score in value.values()):
            raise ValueError("Confidence scores must be between zero and one.")
        return value

    @field_validator("vendor_name", "vendor_address", "reference", "payment_method", "card_brand")
    @classmethod
    def reject_sensitive_sequences(cls, value: str | None) -> str | None:
        if value and _contains_pan(value):
            raise ValueError("Full payment card numbers are not accepted; provide only the last four digits.")
        lowered = (value or "").lower()
        if any(term in lowered for term in ("social insurance number", "bank account", "medical record", "payroll account")):
            raise ValueError("Sensitive banking, payroll, medical, and SIN data are outside receipt intake.")
        return value


class ReceiptExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    media_asset_ids: list[UUID] = Field(min_length=1, max_length=10)


class ReceiptExtractionResponse(BaseModel):
    draft: ReceiptCreate
    model: str


class ReceiptUpdate(ReceiptCreate):
    media_asset_ids: list[UUID] | None = Field(default=None, max_length=10)
    correction_reason: str = Field(min_length=3, max_length=500)
    vendor_id: UUID | None = None
    create_vendor: bool = False
    duplicate_resolution: Literal["not_duplicate"] | None = None
    version: int = Field(ge=1)


class ReceiptAction(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    version: int = Field(ge=1)


class ReceiptLineItemRead(ReceiptLineItemInput):
    id: UUID
    position: int


class ReceiptAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action: str
    actor_email: str
    from_status: str | None
    to_status: str | None
    reason: str | None
    changes_json: dict
    created_at: datetime


class ReceiptRead(BaseModel):
    id: UUID
    status: ReceiptStatus
    submitter_email: str
    media_asset_ids: list[UUID]
    image_hash: str
    vendor_id: UUID | None
    vendor_name: str | None
    vendor_address: str | None
    reference: str | None
    receipt_date: date | None
    receipt_time: str | None
    currency: str
    subtotal: float | None
    discounts: float
    gst: float
    pst: float
    other_tax: float
    tip: float
    total: float | None
    payment_method: str | None
    card_brand: str | None
    card_last_four: str | None
    company_card_id: UUID | None
    employee_email: str | None
    treatment: ReceiptTreatment
    confidence: dict[str, float]
    source_regions: dict[str, SourceRegion]
    flags: list[str]
    duplicate_of_id: UUID | None
    approved_by: str | None
    approved_at: datetime | None
    exported_by: str | None
    exported_at: datetime | None
    version: int
    reconciliation_difference: float | None
    is_balanced: bool
    approval_blockers: list[str]
    line_items: list[ReceiptLineItemRead]
    audit_history: list[ReceiptAuditRead]
    created_at: datetime
    updated_at: datetime


class ReceiptList(BaseModel):
    items: list[ReceiptRead]
    total: int


def _contains_pan(value: str) -> bool:
    digits = "".join(character for character in value if character.isdigit())
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    parity = len(digits) % 2
    for index, character in enumerate(digits):
        number = int(character)
        if index % 2 == parity:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0
