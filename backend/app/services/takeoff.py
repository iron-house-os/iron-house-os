from collections import defaultdict

from app.schemas.takeoff import (
    EstimateReadyItem,
    QuantityRegisterRequest,
    QuantityRegisterResponse,
    QuantitySummaryLine,
)


def summarize_quantity_register(payload: QuantityRegisterRequest) -> QuantityRegisterResponse:
    grouped: dict[tuple[str, str], list] = defaultdict(list)
    estimate_ready_items: list[EstimateReadyItem] = []
    warnings: list[str] = []

    for item in payload.items:
        grouped[(item.category, item.unit)].append(item)
        if item.estimate_ready:
            estimate_ready_items.append(
                EstimateReadyItem(
                    code=item.code,
                    description=item.description,
                    category=item.category,
                    quantity=item.quantity,
                    unit=item.unit,
                    source=item.source,
                    confidence=item.confidence,
                    drawing_reference=item.drawing_reference,
                    notes=item.notes,
                )
            )
        if item.confidence < 0.7:
            warnings.append(f"Low confidence quantity: {item.description}")
        if item.quantity == 0:
            warnings.append(f"Zero quantity item: {item.description}")

    summaries = [
        QuantitySummaryLine(
            category=category,
            unit=unit,
            total_quantity=sum(item.quantity for item in items),
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
        low_confidence_count=sum(1 for item in payload.items if item.confidence < 0.7),
        summaries=summaries,
        estimate_ready_items=estimate_ready_items,
        warnings=warnings,
    )
