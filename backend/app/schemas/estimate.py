from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.equipment_rates import EquipmentRateInput


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
    rate_input: EquipmentRateInput | None = None


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
    is_qualified: bool = True
    qualification_notes: list[str] = Field(default_factory=list)
    is_selected: bool = False
    selection_reason: str | None = None
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


class SmallJobTier(StrEnum):
    one_shift = "1_shift"
    two_to_three_shifts = "2_3_shifts"
    four_to_five_shifts = "4_5_shifts"
    standard = "more_than_5_shifts"


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
    base_hourly_wage: float = Field(default=0, ge=0)
    labour_chargeout_multiplier: float = Field(default=2.1, gt=0)
    target_margin_percent: float = Field(default=10, ge=0, lt=100)
    planned_field_shifts: int | None = Field(default=None, ge=1)
    small_job_tier: SmallJobTier = SmallJobTier.standard
    small_job_premium_percent: float | None = Field(default=None, ge=0)
    calculated_labour_chargeout_rate: float = Field(default=0, ge=0)
    override_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def apply_labour_pricing_standard(self) -> "EstimateCreate":
        tier, expected_premium = labour_pricing_tier(self.planned_field_shifts)
        premium = (
            expected_premium
            if self.small_job_premium_percent is None
            else self.small_job_premium_percent
        )
        needs_reason = (
            self.labour_chargeout_multiplier < 2.1
            or self.target_margin_percent < 10
            or premium < expected_premium
        )
        if needs_reason and not (self.override_reason or "").strip():
            raise ValueError("An override reason is required below an approved labour-pricing default.")
        object.__setattr__(self, "small_job_tier", tier)
        object.__setattr__(self, "small_job_premium_percent", premium)
        rate = round(
            self.base_hourly_wage
            * self.labour_chargeout_multiplier
            * (1 + premium / 100)
        )
        object.__setattr__(self, "calculated_labour_chargeout_rate", rate)
        return self


def labour_pricing_tier(planned_field_shifts: int | None) -> tuple[SmallJobTier, float]:
    if planned_field_shifts == 1:
        return SmallJobTier.one_shift, 25
    if planned_field_shifts is not None and planned_field_shifts <= 3:
        return SmallJobTier.two_to_three_shifts, 20
    if planned_field_shifts is not None and planned_field_shifts <= 5:
        return SmallJobTier.four_to_five_shifts, 15
    return SmallJobTier.standard, 0


class TakeoffHandoffItem(BaseModel):
    code: str | None = None
    description: str = Field(min_length=1)
    category: str
    quantity: float = Field(ge=0)
    unit: EstimateUnit
    source: str | None = None
    confidence: float = Field(default=1, ge=0, le=1)
    drawing_reference: str | None = None
    notes: str | None = None


class EstimateHandoffRequest(BaseModel):
    project_name: str = Field(default="Iron House Estimate", min_length=1)
    project_code: str | None = None
    items: list[TakeoffHandoffItem] = Field(default_factory=list)


class EstimateHandoffResponse(BaseModel):
    project_name: str
    project_code: str | None = None
    line_items: list[EstimateLineItem]
    warnings: list[str]
    assumptions: list[str]


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
    base_hourly_wage: float
    labour_chargeout_multiplier: float
    target_margin_percent: float
    planned_field_shifts: int | None
    small_job_tier: SmallJobTier
    small_job_premium_percent: float
    calculated_labour_chargeout_rate: float
    labour_chargeout_total: float
    override_reason: str | None


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
