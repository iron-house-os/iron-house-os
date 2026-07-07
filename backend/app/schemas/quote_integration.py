from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class QuoteStatus(StrEnum):
    requested = "requested"
    received = "received"
    declined = "declined"
    bounced = "bounced"
    selected = "selected"
    rejected = "rejected"


class QuoteScopeType(StrEnum):
    material = "material"
    subcontract = "subcontract"
    trucking = "trucking"
    disposal = "disposal"
    equipment = "equipment"
    other = "other"


class SupplierQuoteCreate(BaseModel):
    rfq_id: UUID | None = None
    rfq_package_id: UUID | None = None
    supplier_id: UUID | None = None
    supplier_name: str = Field(min_length=1)
    line_item_code: str | None = None
    line_item_description: str | None = None
    scope: str = Field(min_length=1)
    scope_type: QuoteScopeType = QuoteScopeType.material
    status: QuoteStatus = QuoteStatus.received
    amount: float = Field(default=0, ge=0)
    is_selected: bool = False
    selection_reason: str | None = None
    exclusions: list[str] = Field(default_factory=list)
    notes: str | None = None


class SupplierQuoteRead(SupplierQuoteCreate):
    id: UUID | None = None


class QuoteComparisonLine(BaseModel):
    line_item_code: str | None = None
    line_item_description: str
    scope: str
    lowest_supplier: str | None = None
    lowest_amount: float | None = None
    selected_supplier: str | None = None
    selected_amount: float | None = None
    selected_is_lowest: bool = True
    selection_reason: str | None = None
    quote_count: int


class QuoteComparisonRequest(BaseModel):
    quotes: list[SupplierQuoteCreate] = Field(default_factory=list)


class QuoteComparisonResponse(BaseModel):
    lines: list[QuoteComparisonLine]
    total_lowest: float
    total_selected: float
    delta_from_lowest: float
