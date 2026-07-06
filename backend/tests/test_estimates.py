from app.schemas.estimate import (
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
)
from app.services.estimates import calculate_estimate, calculate_line_item


def test_calculate_line_item_self_perform_costs() -> None:
    item = EstimateLineItem(
        description="Install storm pipe",
        quantity=100,
        unit=EstimateUnit.metre,
        production_rate_per_hour=10,
        labour=[LabourCrewMember(role="Pipe layer", quantity=2, hourly_rate=40, burden_percent=25)],
        equipment=[EquipmentResource(name="Excavator", quantity=1, hourly_rate=85)],
        materials=[MaterialInput(name="PVC pipe", quantity=100, unit=EstimateUnit.metre, unit_cost=35)],
    )

    result = calculate_line_item(item)

    assert result.hours == 10
    assert result.labour_cost == 1000
    assert result.equipment_cost == 850
    assert result.material_cost == 3500
    assert result.direct_cost == 5350
    assert result.unit_cost == 53.5


def test_calculate_line_item_material_waste_and_subcontract() -> None:
    item = EstimateLineItem(
        description="Asphalt paving",
        quantity=1,
        materials=[MaterialInput(name="Tack coat", quantity=100, unit_cost=2, waste_percent=10)],
        subcontract=SubcontractInput(subcontractor="Superior Paving", scope="Pave", quoted_amount=15000),
    )

    result = calculate_line_item(item)

    assert result.material_cost == 220
    assert result.subcontract_cost == 15000
    assert result.direct_cost == 15220


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
    assert summary.assumptions == ["Normal working hours"]
    assert summary.exclusions == ["Contaminated soils"]
