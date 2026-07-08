from app.schemas.estimate import (
    DefaultProductionActivity,
    EstimateHandoffRequest,
    EstimateHandoffResponse,
    EstimateItemType,
    EstimateLineItem,
    TakeoffHandoffItem,
)

CATEGORY_ACTIVITY_MAP: dict[str, DefaultProductionActivity | None] = {
    "pipe": DefaultProductionActivity.pipe_installation,
    "structures": DefaultProductionActivity.manhole_installation,
    "asphalt": None,
    "concrete": DefaultProductionActivity.sidewalk,
    "earthworks": DefaultProductionActivity.excavation,
    "landscape": DefaultProductionActivity.landscaping,
    "traffic": DefaultProductionActivity.traffic_control,
    "misc": None,
}

CATEGORY_TYPE_MAP: dict[str, EstimateItemType] = {
    "asphalt": EstimateItemType.subcontract,
    "traffic": EstimateItemType.subcontract,
    "misc": EstimateItemType.allowance,
}


def build_estimate_handoff(payload: EstimateHandoffRequest) -> EstimateHandoffResponse:
    line_items: list[EstimateLineItem] = []
    warnings: list[str] = []

    for index, item in enumerate(payload.items, start=1):
        line_items.append(_to_estimate_line(index, item))
        if item.confidence < 0.7:
            warnings.append(f"Low confidence takeoff item sent to estimating: {item.description}")
        if not item.drawing_reference:
            warnings.append(f"Estimate line is missing drawing reference: {item.description}")
        if item.category == "asphalt":
            warnings.append(f"{item.description} mapped as subcontract pricing until paving supplier quote is entered.")

    assumptions = [
        "Build 30 maps takeoff quantities into estimating line items without overwriting the estimating engine.",
        "Self-perform categories use IHOS default production activities where available.",
        "Asphalt and traffic items are treated as subcontract placeholders until supplier quote pricing is entered.",
        "Generated lines preserve drawing reference and confidence in notes for audit review.",
    ]

    return EstimateHandoffResponse(
        project_name=payload.project_name,
        project_code=payload.project_code,
        line_items=line_items,
        warnings=warnings,
        assumptions=assumptions,
    )


def _to_estimate_line(index: int, item: TakeoffHandoffItem) -> EstimateLineItem:
    item_type = CATEGORY_TYPE_MAP.get(item.category, EstimateItemType.self_perform)
    default_activity = CATEGORY_ACTIVITY_MAP.get(item.category)
    notes = [
        f"Takeoff source: {item.source or 'unknown'}",
        f"Confidence: {item.confidence:.2f}",
    ]
    if item.drawing_reference:
        notes.append(f"Drawing reference: {item.drawing_reference}")
    if item.notes:
        notes.append(item.notes)

    return EstimateLineItem(
        code=item.code or f"EH-{index:03d}",
        description=item.description,
        item_type=item_type,
        quantity=item.quantity,
        unit=item.unit,
        default_activity=default_activity if item_type == EstimateItemType.self_perform else None,
        labour=[],
        equipment=[],
        materials=[],
        disposal=[],
        vendor_quotes=[],
        notes=" | ".join(notes),
    )
