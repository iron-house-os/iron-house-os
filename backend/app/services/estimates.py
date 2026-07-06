from __future__ import annotations

from app.schemas.estimate import EstimateCreate, EstimateLineItem, EstimateLineItemCost, EstimateSummary


def calculate_estimate(payload: EstimateCreate) -> EstimateSummary:
    line_item_costs = [calculate_line_item(item) for item in payload.line_items]
    direct_cost = sum(item.direct_cost for item in line_item_costs)
    indirect_cost = sum(indirect.amount for indirect in payload.indirects)
    risk_cost = sum(risk.amount for risk in payload.risks)
    subtotal_before_markup = direct_cost + indirect_cost + risk_cost
    contingency = subtotal_before_markup * payload.markup.contingency_percent / 100
    overhead_base = subtotal_before_markup + contingency
    overhead = overhead_base * payload.markup.overhead_percent / 100
    profit_base = overhead_base + overhead
    profit = profit_base * payload.markup.profit_percent / 100
    final_price = profit_base + profit
    gross_margin_percent = ((final_price - direct_cost) / final_price * 100) if final_price else 0

    return EstimateSummary(
        project_name=payload.project_name,
        project_code=payload.project_code,
        direct_cost=round(direct_cost, 2),
        indirect_cost=round(indirect_cost, 2),
        risk_cost=round(risk_cost, 2),
        subtotal_before_markup=round(subtotal_before_markup, 2),
        contingency=round(contingency, 2),
        overhead=round(overhead, 2),
        profit=round(profit, 2),
        final_price=round(final_price, 2),
        gross_margin_percent=round(gross_margin_percent, 2),
        line_items=line_item_costs,
        assumptions=payload.assumptions,
        exclusions=payload.exclusions,
    )


def calculate_line_item(item: EstimateLineItem) -> EstimateLineItemCost:
    hours = _calculate_hours(item)
    labour_cost = sum(
        member.quantity * member.burdened_hourly_rate * hours for member in item.labour
    )
    equipment_cost = sum(resource.quantity * resource.hourly_rate * hours for resource in item.equipment)
    material_cost = sum(
        material.quantity * material.unit_cost * (1 + material.waste_percent / 100)
        for material in item.materials
    )
    subcontract_cost = item.subcontract.quoted_amount if item.subcontract else 0
    explicit_direct_cost = item.direct_unit_cost * item.quantity if item.direct_unit_cost is not None else 0
    direct_cost = labour_cost + equipment_cost + material_cost + subcontract_cost + explicit_direct_cost
    unit_cost = direct_cost / item.quantity if item.quantity else 0

    return EstimateLineItemCost(
        description=item.description,
        item_type=item.item_type,
        quantity=item.quantity,
        unit=item.unit,
        hours=round(hours, 2),
        labour_cost=round(labour_cost, 2),
        equipment_cost=round(equipment_cost, 2),
        material_cost=round(material_cost, 2),
        subcontract_cost=round(subcontract_cost, 2),
        direct_cost=round(direct_cost, 2),
        unit_cost=round(unit_cost, 2),
    )


def _calculate_hours(item: EstimateLineItem) -> float:
    if item.production_rate_per_hour:
        return item.quantity / item.production_rate_per_hour
    return 0
