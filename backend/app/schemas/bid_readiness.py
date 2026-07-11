from pydantic import BaseModel, Field


class MunicipalityAdjustment(BaseModel):
    municipality: str
    label: str
    percentage: float = Field(default=0, ge=0)
    fixed_cost: float = Field(default=0, ge=0)
    requirement: str | None = None


class RFQReadinessInput(BaseModel):
    required_categories: list[str] = Field(default_factory=list)
    covered_categories: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    attached_documents: list[str] = Field(default_factory=list)


class QuoteCandidate(BaseModel):
    supplier: str
    amount: float = Field(ge=0)
    scope_complete: bool = True
    exclusions_count: int = Field(default=0, ge=0)
    confidence: float = Field(default=1, ge=0, le=1)


class EquipmentCandidate(BaseModel):
    name: str
    hourly_rate: float = Field(ge=0)
    estimated_hours: float = Field(ge=0)
    mobilization: float = Field(default=0, ge=0)
    fuel_surcharge: float = Field(default=0, ge=0)


class RiskItem(BaseModel):
    label: str
    probability: float = Field(ge=0, le=1)
    impact: float = Field(ge=0)
    included_in_price: bool = False


class BidReadinessRequest(BaseModel):
    project_name: str
    direct_cost: float = Field(ge=0)
    markup_percentage: float = Field(default=30, ge=0)
    municipality_adjustments: list[MunicipalityAdjustment] = Field(default_factory=list)
    rfq: RFQReadinessInput = Field(default_factory=RFQReadinessInput)
    quotes: list[QuoteCandidate] = Field(default_factory=list)
    equipment: list[EquipmentCandidate] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class RankedOption(BaseModel):
    name: str
    total_cost: float
    score: float | None = None
    warnings: list[str] = Field(default_factory=list)


class BidReadinessResponse(BaseModel):
    municipality_cost: float
    adjusted_cost: float
    contingency: float
    recommended_quote: RankedOption | None
    recommended_equipment: RankedOption | None
    rfq_ready: bool
    missing_rfq_categories: list[str]
    missing_rfq_documents: list[str]
    tender_price: float
    package_ready: bool
    blockers: list[str]
    warnings: list[str]
