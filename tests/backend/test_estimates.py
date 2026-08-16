import pytest
from pydantic import ValidationError

from app.schemas.estimate import (
    DefaultProductionActivity,
    DisposalInput,
    EquipmentResource,
    EstimateCreate,
    EstimateIndirect,
    EstimateLineItem,
    EstimateMarkup,
    EstimateRiskAllowance,
    EstimateUnit,
    LabourCrewMember,
    MaterialInput,
    SubcontractInput,
    VendorQuoteInput,
)
from app.services.estimates import calculate_estimate, calculate_line_item, get_rate_library


@pytest.mark.parametrize(
    ("shifts", "tier", "premium", "rate"),
    [
        (1, "1_shift", 25, 105),
        (2, "2_3_shifts", 20, 101),
        (3, "2_3_shifts", 20, 101),
        (4, "4_5_shifts", 15, 97),
        (5, "4_5_shifts", 15, 97),
        (6, "more_than_5_shifts", 0, 84),
    ],
)
def test_labour_pricing_tiers_and_whole_dollar_rounding(
    shifts: int, tier: str, premium: float, rate: float
) -> None:
    estimate = EstimateCreate(
        project_name="Small job",
        base_hourly_wage=40,
        planned_field_shifts=shifts,
    )

    assert estimate.small_job_tier.value == tier
    assert estimate.small_job_premium_percent == premium
    assert estimate.calculated_labour_chargeout_rate == rate


def test_small_job_premium_applies_only_to_labour_chargeout() -> None:
    common = {
        "project_name": "Small excavation",
        "base_hourly_wage": 40,
        "line_items": [
            EstimateLineItem(
                description="Excavate",
                quantity=8,
                unit=EstimateUnit.hour,
                production_rate_per_hour=1,
                labour=[LabourCrewMember(role="Labourer", quantity=1, hourly_rate=40)],
                equipment=[EquipmentResource(name="Excavator", hourly_rate=100)],
                materials=[MaterialInput(name="Pipe", quantity=1, unit_cost=100)],
            )
        ],
    }
    one_shift = calculate_estimate(EstimateCreate(**common, planned_field_shifts=1))
    standard = calculate_estimate(EstimateCreate(**common, planned_field_shifts=6))

    assert one_shift.category_breakdown.equipment == standard.category_breakdown.equipment == 800
    assert one_shift.category_breakdown.material == standard.category_breakdown.material == 100
    assert one_shift.labour_chargeout_total == 840
    assert standard.labour_chargeout_total == 672
    assert one_shift.final_price - standard.final_price == 168


@pytest.mark.parametrize(
    "overrides",
    [
        {"labour_chargeout_multiplier": 2.0},
        {"target_margin_percent": 9},
        {"planned_field_shifts": 1, "small_job_premium_percent": 0},
    ],
)
def test_below_standard_labour_pricing_requires_override_reason(overrides: dict) -> None:
    with pytest.raises(ValidationError, match="override reason"):
        EstimateCreate(project_name="Controlled override", **overrides)


def test_calculate_line_item_self_perform_costs() -> None:
    item = EstimateLineItem(
        description="Install storm pipe",
        quantity=100,
        unit=EstimateUnit.metre,
        production_rate_per_hour=10,
        labour=[
            LabourCrewMember(role="Pipe layer", quantity=2, hourly_rate=40, burden_percent=25)
        ],
        equipment=[EquipmentResource(name="Excavator", quantity=1, hourly_rate=85)],
        materials=[
            MaterialInput(name="PVC pipe", quantity=100, unit=EstimateUnit.metre, unit_cost=35)
        ],
    )

    result = calculate_line_item(item)

    assert result.hours == 10
    assert result.labour_cost == 1000
    assert result.equipment_cost == 850
    assert result.material_cost == 3500
    assert result.direct_cost == 5350
    assert result.unit_cost == 53.5


def test_calculate_line_item_material_waste_disposal_and_subcontract() -> None:
    item = EstimateLineItem(
        description="Asphalt paving",
        quantity=1,
        materials=[MaterialInput(name="Tack coat", quantity=100, unit_cost=2, waste_percent=10)],
        disposal=[
            DisposalInput(material="Asphalt grindings", quantity=12, unit_cost=18, haul_cost=7)
        ],
        subcontract=SubcontractInput(
            subcontractor="Superior Paving", scope="Pave", quoted_amount=15000
        ),
    )

    result = calculate_line_item(item)

    assert result.material_cost == 220
    assert result.disposal_cost == 300
    assert result.subcontract_cost == 15000
    assert result.direct_cost == 15520


def test_vendor_quotes_select_lowest_when_no_quote_marked_selected() -> None:
    item = EstimateLineItem(
        description="Concrete sidewalk subcontract",
        quantity=1,
        vendor_quotes=[
            VendorQuoteInput(supplier="Supplier A", scope="Sidewalk", amount=12500),
            VendorQuoteInput(supplier="Supplier B", scope="Sidewalk", amount=11800),
        ],
    )

    result = calculate_line_item(item)

    assert result.subcontract_cost == 11800
    assert result.selected_quote_supplier == "Supplier B"


def test_vendor_quotes_respect_selected_quote() -> None:
    item = EstimateLineItem(
        description="Asphalt paving subcontract",
        quantity=1,
        vendor_quotes=[
            VendorQuoteInput(supplier="Lowest", scope="Paving", amount=10000),
            VendorQuoteInput(
                supplier="Qualified selected",
                scope="Paving",
                amount=11250,
                is_selected=True,
                selection_reason="Complete scope and schedule",
            ),
        ],
    )

    result = calculate_line_item(item)

    assert result.subcontract_cost == 11250
    assert result.selected_quote_supplier == "Qualified selected"


def test_vendor_quotes_ignore_unqualified_lower_quote() -> None:
    item = EstimateLineItem(
        description="Pipe supply",
        quantity=1,
        vendor_quotes=[
            VendorQuoteInput(
                supplier="Incomplete quote",
                scope="Pipe",
                amount=9000,
                is_qualified=False,
                qualification_notes=["Freight excluded"],
            ),
            VendorQuoteInput(supplier="Qualified quote", scope="Pipe", amount=10000),
        ],
    )

    result = calculate_line_item(item)

    assert result.subcontract_cost == 10000
    assert result.selected_quote_supplier == "Qualified quote"


def test_vendor_quotes_fall_back_to_lowest_when_non_low_selection_has_no_reason() -> None:
    item = EstimateLineItem(
        description="Paving",
        quantity=1,
        vendor_quotes=[
            VendorQuoteInput(supplier="Lowest", scope="Paving", amount=10000),
            VendorQuoteInput(
                supplier="Undocumented selection",
                scope="Paving",
                amount=11250,
                is_selected=True,
            ),
        ],
    )

    result = calculate_line_item(item)

    assert result.subcontract_cost == 10000
    assert result.selected_quote_supplier == "Lowest"


def test_default_production_rate_activity_populates_crew_and_equipment() -> None:
    item = EstimateLineItem(
        description="Excavate trench",
        quantity=60,
        unit=EstimateUnit.cubic_metre,
        default_activity=DefaultProductionActivity.excavation,
    )

    result = calculate_line_item(item)

    assert result.hours == 2
    assert result.labour_cost > 0
    assert result.equipment_cost > 0


def test_calculate_estimate_summary() -> None:
    estimate = EstimateCreate(
        project_name="Marine Drive Parking Lot",
        project_code="WR26-012",
        line_items=[
            EstimateLineItem(
                description="Excavation",
                quantity=100,
                unit=EstimateUnit.cubic_metre,
                direct_unit_cost=25,
            )
        ],
        indirects=[EstimateIndirect(description="Mobilization", amount=1000)],
        risks=[EstimateRiskAllowance(description="Unknown utilities", amount=500)],
        markup=EstimateMarkup(contingency_percent=10, overhead_percent=5, profit_percent=10),
        assumptions=["Normal working hours"],
        exclusions=["Contaminated soils"],
    )

    summary = calculate_estimate(estimate)

    assert summary.direct_cost == 2500
    assert summary.indirect_cost == 1000
    assert summary.risk_cost == 500
    assert summary.subtotal_before_markup == 4000
    assert summary.contingency == 400
    assert summary.overhead == 220
    assert summary.profit == 462
    assert summary.final_price == 5082
    assert summary.gross_margin_percent == 50.81
    assert summary.category_breakdown.indirect == 1000
    assert summary.assumptions == ["Normal working hours"]
    assert summary.exclusions == ["Contaminated soils"]


def test_calculate_estimate_bonding_insurance_and_expected_risk() -> None:
    estimate = EstimateCreate(
        project_name="Utility crossing",
        line_items=[EstimateLineItem(description="Base work", quantity=1, direct_unit_cost=10000)],
        risks=[EstimateRiskAllowance(description="Utility conflict", amount=2000, probability=0.5)],
        markup=EstimateMarkup(
            contingency_percent=5,
            bonding_percent=1,
            insurance_percent=2,
            overhead_percent=10,
            profit_percent=10,
        ),
    )

    summary = calculate_estimate(estimate)

    assert summary.risk_cost == 1000
    assert summary.contingency == 550
    assert summary.bonding == 115.5
    assert summary.insurance == 233.31
    assert summary.overhead == 1189.88
    assert summary.final_price == 14397.56


def test_rate_library_exposes_default_activities() -> None:
    library = get_rate_library()

    activities = {rate.activity for rate in library.production_rates}

    assert DefaultProductionActivity.pipe_installation in activities
    assert DefaultProductionActivity.traffic_control in activities



def test_shared_all_in_equipment_rate_prevents_operator_double_count() -> None:
    from app.schemas.equipment_rates import (
        EquipmentRateInput,
        RateCategory,
        RegionalMarket,
        RentalPeriod,
    )

    item = EstimateLineItem(
        description="Operate rented excavator",
        quantity=8,
        unit=EstimateUnit.hour,
        production_rate_per_hour=1,
        labour=[
            LabourCrewMember(role="Operator", quantity=1, hourly_rate=50),
            LabourCrewMember(role="Labourer", quantity=1, hourly_rate=30),
        ],
        equipment=[
            EquipmentResource(
                name="20-23 t excavator",
                quantity=1,
                hourly_rate=0,
                rate_input=EquipmentRateInput(
                    regional_market=RegionalMarket.surrey_fraser_valley_east,
                    rate_category=RateCategory.equipment,
                    equipment_class="Excavator",
                    equipment_description="20-23 t",
                    operator_included=True,
                    base_rate=800,
                    rental_period=RentalPeriod.day,
                    included_hours=8,
                    target_margin_percent=10,
                    market_benchmark_rate=228,
                    source_name="IEOA 2026 Suggested Equipment Rates",
                ),
            )
        ],
    )

    result = calculate_line_item(item)

    assert result.labour_cost == 240
    assert result.equipment_cost == 800
    assert result.direct_cost == 1040
