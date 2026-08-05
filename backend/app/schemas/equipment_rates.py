from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class RegionalMarket(StrEnum):
    vancouver_metro_west = "vancouver_metro_west"
    surrey_fraser_valley_east = "surrey_fraser_valley_east"


class RateCategory(StrEnum):
    labour = "labour"
    equipment = "equipment"
    attachment = "attachment"
    support_vehicle_light_equipment = "support_vehicle_light_equipment"
    trucking_disposal = "trucking_disposal"
    mobilization_logistics = "mobilization_logistics"


class OwnershipBasis(StrEnum):
    rented = "rented"
    owned = "owned"
    subcontracted = "subcontracted"


class RateBasis(StrEnum):
    industry_benchmark = "industry_benchmark"
    vendor_quote = "vendor_quote"
    owned_cost_model = "owned_cost_model"
    contract_rate = "contract_rate"


class RentalPeriod(StrEnum):
    hour = "hour"
    day = "day"
    week = "week"
    month = "month"


class ApprovalStatus(StrEnum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class EquipmentBenchmark(BaseModel):
    rate_category: RateCategory
    equipment_class: str
    equipment_description: str
    base_rate: float | None = Field(default=None, ge=0)
    operator_included: bool = True
    source_name: str
    source_url: str
    source_effective_date: date
    price_on_request: bool = False


class EquipmentRateInput(BaseModel):
    regional_market: RegionalMarket
    rate_category: RateCategory = RateCategory.equipment
    equipment_class: str = Field(min_length=1)
    equipment_description: str = Field(min_length=1)
    ownership_basis: OwnershipBasis = OwnershipBasis.rented
    rate_basis: RateBasis = RateBasis.vendor_quote
    operator_included: bool = False
    base_rate: float = Field(default=0, ge=0)
    rental_period: RentalPeriod = RentalPeriod.hour
    included_hours: float = Field(default=1, gt=0)
    overtime_hour_rate: float = Field(default=0, ge=0)
    fuel_included: bool = True
    fuel_cost: float = Field(default=0, ge=0)
    fuel_surcharge_percent: float = Field(default=0, ge=0)
    damage_waiver_percent_or_amount: float = Field(default=0, ge=0)
    damage_waiver_is_percent: bool = True
    rental_fees: float = Field(default=0, ge=0)
    attachment_rate: float = Field(default=0, ge=0)
    delivery_cost: float = Field(default=0, ge=0)
    pickup_cost: float = Field(default=0, ge=0)
    cleanup_allowance: float = Field(default=0, ge=0)
    operator_hourly_cost: float = Field(default=0, ge=0)
    project_support_hourly_cost: float = Field(default=0, ge=0)
    mobilization_rate: float = Field(default=0, ge=0)
    minimum_billable_hours: float = Field(default=4, ge=0)
    standby_rate: float = Field(default=0, ge=0)
    target_margin_percent: float = Field(default=10, ge=0, lt=100)
    market_benchmark_rate: float | None = Field(default=None, ge=0)
    contract_rate: float | None = Field(default=None, ge=0)
    source_name: str = ""
    source_url: str = ""
    source_effective_date: date | None = None
    quote_expiry_date: date | None = None
    override_reason: str | None = None
    approval_status: ApprovalStatus = ApprovalStatus.draft
    waive_mobilization: bool = False
    waive_minimum: bool = False
    operator_inclusion_changed: bool = False

    @model_validator(mode="after")
    def validate_period_and_contract(self) -> EquipmentRateInput:
        if self.rental_period != RentalPeriod.hour and self.included_hours <= 0:
            raise ValueError("Day, week, and month rates require included_hours.")
        if self.rate_basis == RateBasis.contract_rate and self.contract_rate is None:
            raise ValueError("Contract-rate pricing requires contract_rate.")
        return self


class EquipmentRateResult(BaseModel):
    hourly_base_rate: float
    hourly_rental_direct_cost: float
    hourly_all_in_direct_cost: float
    calculated_client_rate: float
    selected_client_rate: float
    minimum_billable_amount: float
    standby_rate: float
    operator_labour_to_add: float
    approval_required: bool
    approval_reasons: list[str]
    approval_status: ApprovalStatus
    source_name: str
    audit_components: dict[str, float]


class EquipmentRateLibrary(BaseModel):
    regional_markets: list[RegionalMarket]
    benchmarks: list[EquipmentBenchmark]
    default_target_margin_percent: float = 10
    currency: str = "CAD"
    gst_included: bool = False


class ClientRateSheetRequest(BaseModel):
    title: str = Field(default="Iron House Client Rate Sheet", min_length=1)
    effective_date: date
    expiry_date: date
    regional_market: RegionalMarket
    lines: list[EquipmentRateInput] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    executive_approved: bool = False
    approval_reference: str | None = None

    @model_validator(mode="after")
    def validate_issue_gate(self) -> ClientRateSheetRequest:
        if self.expiry_date < self.effective_date:
            raise ValueError("Rate-sheet expiry cannot precede its effective date.")
        if self.executive_approved and not (self.approval_reference or "").strip():
            raise ValueError("Executive approval requires an approval reference.")
        return self
