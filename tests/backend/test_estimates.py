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
                supplier="Qualified selected", scope="Paving", amount=11250, is_selected=True
            ),
        ],
    )

    result = calculate_line_item(item)

    assert result.subcontract_cost == 11250
    assert result.selected_quote_supplier == "Qualified selected"


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
