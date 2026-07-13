from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.estimate import EstimateLineItem


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
    quote_reference: str | None = None
    revision: int = Field(default=1, ge=1)
    line_item_code: str | None = None
    line_item_description: str | None = None
    scope: str = Field(min_length=1)
    scope_type: QuoteScopeType = QuoteScopeType.material
    status: QuoteStatus = QuoteStatus.received
    amount: float = Field(default=0, ge=0)
    is_qualified: bool = True
    qualification_notes: list[str] = Field(default_factory=list)
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
    scope_type: QuoteScopeType
    lowest_supplier: str | None = None
    lowest_amount: float | None = None
    selected_supplier: str | None = None
    selected_amount: float | None = None
    selected_is_lowest: bool = True
    selection_reason: str | None = None
    quote_count: int
    qualified_quote_count: int
    ready_for_estimate: bool
    blockers: list[str] = Field(default_factory=list)


class QuoteComparisonRequest(BaseModel):
    quotes: list[SupplierQuoteCreate] = Field(default_factory=list)


class QuoteComparisonResponse(BaseModel):
    lines: list[QuoteComparisonLine]
    total_lowest: float
    total_selected: float
    delta_from_lowest: float
    ready_for_estimate: bool
    blockers: list[str] = Field(default_factory=list)


class QuoteSelectionDecision(BaseModel):
    line_item_code: str | None = None
    line_item_description: str
    scope: str
    scope_type: QuoteScopeType
    lowest_qualified_supplier: str | None = None
    lowest_qualified_amount: float | None = None
    selected_supplier: str | None = None
    selected_amount: float | None = None
    selected_is_lowest: bool = True
    selection_reason: str | None = None
    quote_count: int
    qualified_quote_count: int
    ready_for_estimate: bool
    blockers: list[str] = Field(default_factory=list)


class QuoteEstimateSelectionRequest(BaseModel):
    quotes: list[SupplierQuoteCreate] = Field(default_factory=list)


class QuoteEstimateSelectionResponse(BaseModel):
    decisions: list[QuoteSelectionDecision]
    line_items: list[EstimateLineItem]
    ready_for_estimate: bool
    blockers: list[str] = Field(default_factory=list)


class QuoteEstimateImportRequest(BaseModel):
    quotes: list[SupplierQuoteCreate] = Field(default_factory=list)
    include_superseded_revisions: bool = False
    minimum_mapping_confidence: float = Field(default=0.5, ge=0, le=1)


class QuoteEstimateLine(BaseModel):
    supplier_name: str
    quote_reference: str | None = None
    revision: int
    scope: str
    scope_type: QuoteScopeType
    amount: float
    cost_code: str | None = None
    cost_code_name: str | None = None
    mapping_confidence: float = Field(ge=0, le=1)
    needs_review: bool
    exclusions: list[str] = Field(default_factory=list)
    notes: str | None = None


class QuoteRevisionSummary(BaseModel):
    supplier_name: str
    quote_reference: str | None = None
    current_revision: int
    superseded_revisions: list[int] = Field(default_factory=list)


class QuoteEstimateImportResponse(BaseModel):
    lines: list[QuoteEstimateLine]
    revisions: list[QuoteRevisionSummary]
    mapped_count: int
    review_count: int
    total_amount: float
    warnings: list[str] = Field(default_factory=list)
