from enum import StrEnum

from pydantic import BaseModel, Field


class EstimateItemType(StrEnum):
    self_perform = "self_perform"
    material = "material"
    subcontract = "subcontract"
    indirect = "indirect"
    allowance = "allowance"


class EstimateUnit(StrEnum):
    lump_sum = "LS"
    each = "EA"
    metre = "m"
    square_metre = "m2"
    cubic_metre = "m3"
    tonne = "t"
    hour = "hr"
    day = "day"


class CostCategory(StrEnum):
    labour = "labour"
    equipment = "equipment"
    material = "material"
    subcontract = "subcontract"
    disposal = "disposal"
    indirect = "indirect"
    risk = "risk"


class DefaultProductionActivity(StrEnum):
    pipe_installation = "pipe_installation"
    excavation = "excavation"
    bedding = "bedding"
    backfill = "backfill"
    asphalt_removal = "asphalt_removal"
    concrete_removal = "concrete_removal"
    manhole_installation = "manhole_installation"
    catch_basin_installation = "catch_basin_installation"
    sidewalk = "sidewalk"
    curb = "curb"
    traffic_control = "traffic_control"
    landscaping = "landscaping"


class LabourCrewMember(BaseModel):
    role: str = Field(min_length=1)
    quantity: float = Field(default=1, ge=0)
    hourly_rate: float = Field(default=0, ge=0)
    burden_percent: float = Field(default=0, ge=0)

    @property
    def burdened_hourly_rate(self) -> float:
        return self.hourly_rate * (1 + self.burden_percent / 100)


class EquipmentResource(BaseModel):
    name: str = Field(min_length=1)
    quantity: float = Field(default=1, ge=0)
    hourly_rate: float = Field(default=0, ge=0)
    daily_rate: float | None = Field(default=None, ge=0)
    owned_or_rented: str | None = None


class MaterialInput(BaseModel):
    name: str = Field(min_length=1)
    quantity: float = Field(default=0, ge=0)
    unit: EstimateUnit = EstimateUnit.each
    unit_cost: float = Field(default=0, ge=0)
    supplier: str | None = None
    waste_percent: float = Field(default=0, ge=0)


class DisposalInput(BaseModel):
    material: str = Field(min_length=1)
    quantity: float = Field(default=0, ge=0)
    unit: EstimateUnit = EstimateUnit.tonne
    unit_cost: float = Field(default=0, ge=0)
    haul_cost: float = Field(default=0, ge=0)
    facility: str | None = None


class SubcontractInput(BaseModel):
    subcontractor: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    quoted_amount: float = Field(default=0, ge=0)
    exclusions: list[str] = Field(default_factory=list)
    notes: str | None = None


class VendorQuoteInput(BaseModel):
    supplier: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    amount: float = Field(default=0, ge=0)
    is_selected: bool = False
    notes: str | None = None


class EstimateLineItem(BaseModel):
    code: str | None = None
    description: str = Field(min_length=1)
    item_type: EstimateItemType = EstimateItemType.self_perform
    quantity: float = Field(default=1, ge=0)
    unit: EstimateUnit = EstimateUnit.lump_sum
    production_rate_per_hour: float | None = Field(default=None, gt=0)
    default_activity: DefaultProductionActivity | None = None
    labour: list[LabourCrewMember] = Field(default_factory=list)
    equipment: list[EquipmentResource] = Field(default_factory=list)
    materials: list[MaterialInput] = Field(default_factory=list)
    disposal: list[DisposalInput] = Field(default_factory=list)
    subcontract: SubcontractInput | None = None
    vendor_quotes: list[VendorQuoteInput] = Field(default_factory=list)
    direct_unit_cost: float | None = Field(default=None, ge=0)
    notes: str | None = None


class EstimateIndirect(BaseModel):
    description: str = Field(min_length=1)
    amount: float = Field(default=0, ge=0)
    category: str | None = None


class EstimateRiskAllowance(BaseModel):
    description: str = Field(min_length=1)
    amount: float = Field(default=0, ge=0)
    probability: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None


class EstimateMarkup(BaseModel):
    overhead_percent: float = Field(default=0, ge=0)
    profit_percent: float = Field(default=0, ge=0)
    contingency_percent: float = Field(default=0, ge=0)
    bonding_percent: float = Field(default=0, ge=0)
    insurance_percent: float = Field(default=0, ge=0)


class EstimateCreate(BaseModel):
    project_name: str = Field(min_length=1)
    project_code: str | None = None
    owner: str | None = None
    estimator: str | None = None
    line_items: list[EstimateLineItem] = Field(default_factory=list)
    indirects: list[EstimateIndirect] = Field(default_factory=list)
    risks: list[EstimateRiskAllowance] = Field(default_factory=list)
    markup: EstimateMarkup = Field(default_factory=EstimateMarkup)
    assumptions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class EstimateLineItemCost(BaseModel):
    code: str | None = None
    description: str
    item_type: EstimateItemType
    quantity: float
    unit: EstimateUnit
    hours: float
    labour_cost: float
    equipment_cost: float
    material_cost: float
    disposal_cost: float
    subcontract_cost: float
    direct_cost: float
    unit_cost: float
    selected_quote_supplier: str | None = None
    selected_quote_amount: float | None = None


class EstimateCategoryBreakdown(BaseModel):
    labour: float
    equipment: float
    material: float
    disposal: float
    subcontract: float
    indirect: float
    risk: float


class EstimateSummary(BaseModel):
    project_name: str
    project_code: str | None = None
    direct_cost: float
    indirect_cost: float
    risk_cost: float
    subtotal_before_markup: float
    contingency: float
    bonding: float
    insurance: float
    overhead: float
    profit: float
    final_price: float
    gross_margin_percent: float
    category_breakdown: EstimateCategoryBreakdown
    line_items: list[EstimateLineItemCost]
    assumptions: list[str]
    exclusions: list[str]


class ProductionRate(BaseModel):
    activity: DefaultProductionActivity
    description: str
    unit: EstimateUnit
    production_rate_per_hour: float
    crew: list[LabourCrewMember]
    equipment: list[EquipmentResource]
    notes: str | None = None


class RateLibrary(BaseModel):
    production_rates: list[ProductionRate]
