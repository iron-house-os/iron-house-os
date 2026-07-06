from __future__ import annotations

from app.schemas.estimate import (
    DefaultProductionActivity,
    EquipmentResource,
    EstimateCategoryBreakdown,
    EstimateCreate,
    EstimateLineItem,
    EstimateLineItemCost,
    EstimateSummary,
    EstimateUnit,
    LabourCrewMember,
    ProductionRate,
    RateLibrary,
)


DEFAULT_PRODUCTION_RATES: dict[DefaultProductionActivity, ProductionRate] = {
    DefaultProductionActivity.pipe_installation: ProductionRate(
        activity=DefaultProductionActivity.pipe_installation,
        description="Install municipal pipe including trench, bedding, pipe placement, and initial backfill",
        unit=EstimateUnit.metre,
        production_rate_per_hour=7.5,
        crew=[
            LabourCrewMember(role="Foreman/operator", quantity=1, hourly_rate=58, burden_percent=25),
            LabourCrewMember(role="Pipe layer", quantity=1, hourly_rate=44, burden_percent=25),
            LabourCrewMember(role="Labourer", quantity=2, hourly_rate=36, burden_percent=25),
        ],
        equipment=[
            EquipmentResource(name="Excavator", quantity=1, hourly_rate=145, owned_or_rented="rented"),
            EquipmentResource(name="Skid steer", quantity=1, hourly_rate=85, owned_or_rented="rented"),
        ],
        notes="Default assumes normal depth, open access, and no dewatering or shoring.",
    ),
    DefaultProductionActivity.excavation: ProductionRate(
        activity=DefaultProductionActivity.excavation,
        description="Bulk excavation and loading",
        unit=EstimateUnit.cubic_metre,
        production_rate_per_hour=30,
        crew=[
            LabourCrewMember(role="Operator", quantity=1, hourly_rate=55, burden_percent=25),
            LabourCrewMember(role="Labourer/spotter", quantity=1, hourly_rate=36, burden_percent=25),
        ],
        equipment=[EquipmentResource(name="Excavator", quantity=1, hourly_rate=145, owned_or_rented="rented")],
    ),
    DefaultProductionActivity.bedding: ProductionRate(
        activity=DefaultProductionActivity.bedding,
        description="Place and shape pipe bedding",
        unit=EstimateUnit.cubic_metre,
        production_rate_per_hour=12,
        crew=[
            LabourCrewMember(role="Operator", quantity=1, hourly_rate=55, burden_percent=25),
            LabourCrewMember(role="Labourer", quantity=2, hourly_rate=36, burden_percent=25),
        ],
        equipment=[EquipmentResource(name="Skid steer", quantity=1, hourly_rate=85, owned_or_rented="rented")],
    ),
    DefaultProductionActivity.backfill: ProductionRate(
        activity=DefaultProductionActivity.backfill,
        description="Place and compact trench backfill",
        unit=EstimateUnit.cubic_metre,
        production_rate_per_hour=18,
        crew=[
            LabourCrewMember(role="Operator", quantity=1, hourly_rate=55, burden_percent=25),
            LabourCrewMember(role="Labourer", quantity=1, hourly_rate=36, burden_percent=25),
        ],
        equipment=[
            EquipmentResource(name="Skid steer", quantity=1, hourly_rate=85, owned_or_rented="rented"),
            EquipmentResource(name="Plate tamper/packer", quantity=1, hourly_rate=18, owned_or_rented="rented"),
        ],
    ),
    DefaultProductionActivity.asphalt_removal: ProductionRate(
        activity=DefaultProductionActivity.asphalt_removal,
        description="Sawcut, break, remove, and load asphalt",
        unit=EstimateUnit.square_metre,
        production_rate_per_hour=35,
        crew=[
            LabourCrewMember(role="Operator", quantity=1, hourly_rate=55, burden_percent=25),
            LabourCrewMember(role="Labourer", quantity=1, hourly_rate=36, burden_percent=25),
        ],
        equipment=[
            EquipmentResource(name="Skid steer with breaker/bucket", quantity=1, hourly_rate=95, owned_or_rented="rented")
        ],
    ),
    DefaultProductionActivity.concrete_removal: ProductionRate(
        activity=DefaultProductionActivity.concrete_removal,
        description="Break, remove, and load concrete flatwork/curb",
        unit=EstimateUnit.square_metre,
        production_rate_per_hour=18,
        crew=[
            LabourCrewMember(role="Operator", quantity=1, hourly_rate=55, burden_percent=25),
            LabourCrewMember(role="Labourer", quantity=2, hourly_rate=36, burden_percent=25),
        ],
        equipment=[
            EquipmentResource(name="Skid steer with breaker/bucket", quantity=1, hourly_rate=95, owned_or_rented="rented")
        ],
    ),
    DefaultProductionActivity.manhole_installation: ProductionRate(
        activity=DefaultProductionActivity.manhole_installation,
        description="Install precast manhole barrel/base/top excluding structure supply",
        unit=EstimateUnit.each,
        production_rate_per_hour=0.45,
        crew=[
            LabourCrewMember(role="Foreman/operator", quantity=1, hourly_rate=58, burden_percent=25),
            LabourCrewMember(role="Pipe layer", quantity=1, hourly_rate=44, burden_percent=25),
            LabourCrewMember(role="Labourer", quantity=2, hourly_rate=36, burden_percent=25),
        ],
        equipment=[EquipmentResource(name="Excavator", quantity=1, hourly_rate=145, owned_or_rented="rented")],
    ),
    DefaultProductionActivity.catch_basin_installation: ProductionRate(
        activity=DefaultProductionActivity.catch_basin_installation,
        description="Install catch basin structure excluding structure supply",
        unit=EstimateUnit.each,
        production_rate_per_hour=0.75,
        crew=[
            LabourCrewMember(role="Operator", quantity=1, hourly_rate=55, burden_percent=25),
            LabourCrewMember(role="Pipe layer", quantity=1, hourly_rate=44, burden_percent=25),
            LabourCrewMember(role="Labourer", quantity=1, hourly_rate=36, burden_percent=25),
        ],
        equipment=[EquipmentResource(name="Excavator", quantity=1, hourly_rate=145, owned_or_rented="rented")],
    ),
    DefaultProductionActivity.sidewalk: ProductionRate(
        activity=DefaultProductionActivity.sidewalk,
        description="Prep and place sidewalk by concrete subcontractor support crew",
        unit=EstimateUnit.square_metre,
        production_rate_per_hour=20,
        crew=[LabourCrewMember(role="Labourer", quantity=1, hourly_rate=36, burden_percent=25)],
        equipment=[EquipmentResource(name="Skid steer", quantity=1, hourly_rate=85, owned_or_rented="rented")],
    ),
    DefaultProductionActivity.curb: ProductionRate(
        activity=DefaultProductionActivity.curb,
        description="Prep curb line by concrete subcontractor support crew",
        unit=EstimateUnit.metre,
        production_rate_per_hour=25,
        crew=[LabourCrewMember(role="Labourer", quantity=1, hourly_rate=36, burden_percent=25)],
        equipment=[EquipmentResource(name="Skid steer", quantity=1, hourly_rate=85, owned_or_rented="rented")],
    ),
    DefaultProductionActivity.traffic_control: ProductionRate(
        activity=DefaultProductionActivity.traffic_control,
        description="Traffic control allowance by day",
        unit=EstimateUnit.day,
        production_rate_per_hour=0.125,
        crew=[LabourCrewMember(role="TCP", quantity=2, hourly_rate=42, burden_percent=20)],
        equipment=[],
    ),
    DefaultProductionActivity.landscaping: ProductionRate(
        activity=DefaultProductionActivity.landscaping,
        description="Topsoil, rake, and landscape restoration",
        unit=EstimateUnit.square_metre,
        production_rate_per_hour=25,
        crew=[
            LabourCrewMember(role="Operator", quantity=1, hourly_rate=55, burden_percent=25),
            LabourCrewMember(role="Labourer", quantity=1, hourly_rate=36, burden_percent=25),
        ],
        equipment=[EquipmentResource(name="Skid steer", quantity=1, hourly_rate=85, owned_or_rented="rented")],
    ),
}


def get_rate_library() -> RateLibrary:
    return RateLibrary(production_rates=list(DEFAULT_PRODUCTION_RATES.values()))


def calculate_estimate(payload: EstimateCreate) -> EstimateSummary:
    normalized_items = [_apply_default_rate(item) for item in payload.line_items]
    line_item_costs = [calculate_line_item(item) for item in normalized_items]

    direct_cost = sum(item.direct_cost for item in line_item_costs)
    indirect_cost = sum(indirect.amount for indirect in payload.indirects)
    risk_cost = sum(_expected_risk_amount(risk.amount, risk.probability) for risk in payload.risks)

    subtotal_before_markup = direct_cost + indirect_cost + risk_cost
    contingency = subtotal_before_markup * payload.markup.contingency_percent / 100
    bonding = (subtotal_before_markup + contingency) * payload.markup.bonding_percent / 100
    insurance = (subtotal_before_markup + contingency + bonding) * payload.markup.insurance_percent / 100
    overhead_base = subtotal_before_markup + contingency + bonding + insurance
    overhead = overhead_base * payload.markup.overhead_percent / 100
    profit_base = overhead_base + overhead
    profit = profit_base * payload.markup.profit_percent / 100
    final_price = profit_base + profit
    gross_margin_percent = ((final_price - direct_cost) / final_price * 100) if final_price else 0

    return EstimateSummary(
        project_name=payload.project_name,
        project_code=payload.project_code,
        direct_cost=_round_money(direct_cost),
        indirect_cost=_round_money(indirect_cost),
        risk_cost=_round_money(risk_cost),
        subtotal_before_markup=_round_money(subtotal_before_markup),
        contingency=_round_money(contingency),
        bonding=_round_money(bonding),
        insurance=_round_money(insurance),
        overhead=_round_money(overhead),
        profit=_round_money(profit),
        final_price=_round_money(final_price),
        gross_margin_percent=round(gross_margin_percent, 2),
        category_breakdown=_category_breakdown(line_item_costs, indirect_cost, risk_cost),
        line_items=line_item_costs,
        assumptions=payload.assumptions,
        exclusions=payload.exclusions,
    )


def calculate_line_item(item: EstimateLineItem) -> EstimateLineItemCost:
    item = _apply_default_rate(item)
    hours = _calculate_hours(item)
    labour_cost = sum(
        member.quantity * member.burdened_hourly_rate * hours for member in item.labour
    )
    equipment_cost = sum(resource.quantity * resource.hourly_rate * hours for resource in item.equipment)
    material_cost = sum(
        material.quantity * material.unit_cost * (1 + material.waste_percent / 100)
        for material in item.materials
    )
    disposal_cost = sum(disposal.quantity * (disposal.unit_cost + disposal.haul_cost) for disposal in item.disposal)
    selected_quote = _selected_vendor_quote(item)
    subcontract_cost = selected_quote.amount if selected_quote else 0
    if not selected_quote and item.subcontract:
        subcontract_cost = item.subcontract.quoted_amount
    explicit_direct_cost = item.direct_unit_cost * item.quantity if item.direct_unit_cost is not None else 0
    direct_cost = labour_cost + equipment_cost + material_cost + disposal_cost + subcontract_cost + explicit_direct_cost
    unit_cost = direct_cost / item.quantity if item.quantity else 0

    return EstimateLineItemCost(
        code=item.code,
        description=item.description,
        item_type=item.item_type,
        quantity=item.quantity,
        unit=item.unit,
        hours=round(hours, 2),
        labour_cost=_round_money(labour_cost),
        equipment_cost=_round_money(equipment_cost),
        material_cost=_round_money(material_cost),
        disposal_cost=_round_money(disposal_cost),
        subcontract_cost=_round_money(subcontract_cost),
        direct_cost=_round_money(direct_cost),
        unit_cost=_round_money(unit_cost),
        selected_quote_supplier=selected_quote.supplier if selected_quote else None,
        selected_quote_amount=_round_money(selected_quote.amount) if selected_quote else None,
    )


def _apply_default_rate(item: EstimateLineItem) -> EstimateLineItem:
    if not item.default_activity:
        return item
    rate = DEFAULT_PRODUCTION_RATES[item.default_activity]
    updates = {}
    if item.production_rate_per_hour is None:
        updates["production_rate_per_hour"] = rate.production_rate_per_hour
    if not item.labour:
        updates["labour"] = rate.crew
    if not item.equipment:
        updates["equipment"] = rate.equipment
    if updates:
        return item.model_copy(update=updates)
    return item


def _calculate_hours(item: EstimateLineItem) -> float:
    if item.production_rate_per_hour:
        return item.quantity / item.production_rate_per_hour
    return 0


def _selected_vendor_quote(item: EstimateLineItem):
    selected_quotes = [quote for quote in item.vendor_quotes if quote.is_selected]
    if selected_quotes:
        return min(selected_quotes, key=lambda quote: quote.amount)
    if item.vendor_quotes:
        return min(item.vendor_quotes, key=lambda quote: quote.amount)
    return None


def _expected_risk_amount(amount: float, probability: float | None) -> float:
    if probability is None:
        return amount
    return amount * probability


def _category_breakdown(
    line_items: list[EstimateLineItemCost],
    indirect_cost: float,
    risk_cost: float,
) -> EstimateCategoryBreakdown:
    return EstimateCategoryBreakdown(
        labour=_round_money(sum(item.labour_cost for item in line_items)),
        equipment=_round_money(sum(item.equipment_cost for item in line_items)),
        material=_round_money(sum(item.material_cost for item in line_items)),
        disposal=_round_money(sum(item.disposal_cost for item in line_items)),
        subcontract=_round_money(sum(item.subcontract_cost for item in line_items)),
        indirect=_round_money(indirect_cost),
        risk=_round_money(risk_cost),
    )


def _round_money(value: float) -> float:
    return round(value + 1e-9, 2)
