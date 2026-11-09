from collections import defaultdict

from app.schemas.takeoff import (
    EstimateReadyItem,
    QuantityItem,
    QuantityRegisterRequest,
    QuantityRegisterResponse,
    QuantitySummaryLine,
    TakeoffEngineRequest,
    TakeoffEngineResponse,
    TakeoffReadinessCheck,
)

LOW_CONFIDENCE_THRESHOLD = 0.7
REVIEW_CONFIDENCE_THRESHOLD = 0.85


def summarize_quantity_register(payload: QuantityRegisterRequest) -> QuantityRegisterResponse:
    grouped: dict[tuple[str, str], list[QuantityItem]] = defaultdict(list)
    estimate_ready_items: list[EstimateReadyItem] = []
    warnings: list[str] = []

    for item in payload.items:
        grouped[(item.category, item.unit)].append(item)
        if item.estimate_ready:
            estimate_ready_items.append(_to_estimate_ready_item(item))
        if item.confidence < LOW_CONFIDENCE_THRESHOLD:
            warnings.append(f"Low confidence quantity: {item.description}")
        if item.quantity == 0:
            warnings.append(f"Zero quantity item: {item.description}")
        if item.source in {"drawing_intelligence", "ocr", "takeoff_engine"} and not item.drawing_reference:
            warnings.append(f"Drawing-derived item missing reference: {item.description}")

    summaries = [
        QuantitySummaryLine(
            category=category,
            unit=unit,
            total_quantity=round(sum(item.quantity for item in items), 3),
            item_count=len(items),
            estimate_ready_count=sum(1 for item in items if item.estimate_ready),
        )
        for (category, unit), items in sorted(grouped.items())
    ]

    return QuantityRegisterResponse(
        project_name=payload.project_name,
        project_id=payload.project_id,
        item_count=len(payload.items),
        estimate_ready_count=len(estimate_ready_items),
        low_confidence_count=sum(1 for item in payload.items if item.confidence < LOW_CONFIDENCE_THRESHOLD),
        summaries=summaries,
        estimate_ready_items=estimate_ready_items,
        warnings=warnings,
    )


def run_takeoff_engine(payload: TakeoffEngineRequest) -> TakeoffEngineResponse:
    generated_items = [_rule_to_quantity_item(index, rule) for index, rule in enumerate(payload.extraction_rules, start=1)]
    all_items = [*payload.manual_items, *generated_items]
    register = summarize_quantity_register(
        QuantityRegisterRequest(project_name=payload.project_name, project_id=payload.project_id, items=all_items)
    )

    readiness_checks = _build_readiness_checks(payload, all_items, register)
    conflicts = _detect_conflicts(payload, all_items)
    assumptions = _build_assumptions(payload, generated_items)
    next_actions = _build_next_actions(readiness_checks, conflicts, register)

    return TakeoffEngineResponse(
        project_name=payload.project_name,
        project_id=payload.project_id,
        drawing_set_name=payload.drawing_set_name,
        sheets_reviewed=len(payload.sheets),
        generated_items=generated_items,
        quantity_register=register,
        readiness_checks=readiness_checks,
        estimating_handoff_items=register.estimate_ready_items,
        assumptions=assumptions,
        conflicts=conflicts,
        next_actions=next_actions,
    )


def _rule_to_quantity_item(index: int, rule) -> QuantityItem:
    quantity = rule.measured_value * rule.multiplier * (1 + rule.waste_factor)
    estimate_ready = quantity > 0 and rule.confidence >= LOW_CONFIDENCE_THRESHOLD and bool(rule.drawing_reference)
    return QuantityItem(
        code=f"TQ-{index:03d}",
        description=rule.description,
        category=rule.category,
        quantity=round(quantity, 3),
        unit=rule.unit,
        source="takeoff_engine",
        confidence=rule.confidence,
        estimate_ready=estimate_ready,
        drawing_reference=rule.drawing_reference,
        notes=rule.notes,
        takeoff_method=rule.method,
    )


def _to_estimate_ready_item(item: QuantityItem) -> EstimateReadyItem:
    return EstimateReadyItem(
        code=item.code,
        description=item.description,
        category=item.category,
        quantity=item.quantity,
        unit=item.unit,
        source=item.source,
        confidence=item.confidence,
        drawing_reference=item.drawing_reference,
        notes=item.notes,
        takeoff_method=item.takeoff_method,
        scale=item.scale,
        revision=item.revision,
    )


def _build_readiness_checks(
    payload: TakeoffEngineRequest,
    items: list[QuantityItem],
    register: QuantityRegisterResponse,
) -> list[TakeoffReadinessCheck]:
    return [
        TakeoffReadinessCheck(
            label="Drawing sheets",
            status="ready" if payload.sheets else "review",
            detail=f"{len(payload.sheets)} sheets registered for takeoff review.",
        ),
        TakeoffReadinessCheck(
            label="Scale coverage",
            status="ready" if payload.sheets and all(sheet.scale for sheet in payload.sheets) else "review",
            detail="All sheets have scales." if payload.sheets and all(sheet.scale for sheet in payload.sheets) else "One or more sheets need scale confirmation.",
        ),
        TakeoffReadinessCheck(
            label="Estimate handoff",
            status="ready" if register.estimate_ready_count == len(items) and items else "review",
            detail=f"{register.estimate_ready_count} of {len(items)} quantities are estimate-ready.",
        ),
        TakeoffReadinessCheck(
            label="Confidence",
            status="ready" if register.low_confidence_count == 0 else "blocked",
            detail=f"{register.low_confidence_count} low-confidence quantities require review.",
        ),
    ]


def _detect_conflicts(payload: TakeoffEngineRequest, items: list[QuantityItem]) -> list[str]:
    conflicts: list[str] = []
    sheet_refs = {sheet.sheet_number for sheet in payload.sheets}
    for item in items:
        if item.quantity == 0:
            conflicts.append(f"{item.description} has a zero quantity.")
        if item.drawing_reference and sheet_refs and item.drawing_reference not in sheet_refs:
            conflicts.append(f"{item.description} references {item.drawing_reference}, which is not in the registered sheet list.")
        if item.confidence < REVIEW_CONFIDENCE_THRESHOLD:
            conflicts.append(f"{item.description} should be reviewed before bid finalization; confidence is {item.confidence:.2f}.")
    return conflicts


def _build_assumptions(payload: TakeoffEngineRequest, generated_items: list[QuantityItem]) -> list[str]:
    assumptions = [
        "Build 29 produces a deterministic takeoff register from entered drawing metadata and extraction rules; it does not yet parse PDF geometry directly.",
        "Quantities generated from extraction rules include multiplier and waste factor before rounding.",
        "Only quantities with a drawing reference, non-zero quantity, and confidence at or above 0.70 are marked estimate-ready.",
    ]
    if payload.sheets:
        assumptions.append("Drawing sheet metadata is treated as the current drawing set for readiness checks.")
    if generated_items:
        assumptions.append("Generated takeoff items are tagged as takeoff_engine source for later audit and estimating handoff.")
    return assumptions


def _build_next_actions(
    readiness_checks: list[TakeoffReadinessCheck],
    conflicts: list[str],
    register: QuantityRegisterResponse,
) -> list[str]:
    actions: list[str] = []
    if any(check.status != "ready" for check in readiness_checks):
        actions.append("Confirm missing sheet scales, references, and low-confidence quantities before bid finalization.")
    if conflicts:
        actions.append("Resolve takeoff conflicts and rerun the engine to refresh the estimate-ready BOQ.")
    if register.estimate_ready_items:
        actions.append("Push estimate-ready items into the estimating engine and RFQ package builder.")
    if not actions:
        actions.append("Takeoff register is ready for estimating handoff.")
    return actions
