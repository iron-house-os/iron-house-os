from collections import defaultdict

from app.schemas.takeoff import EstimateReadyItem, QuantityItem
from app.schemas.takeoff_normalization import (
    TakeoffDuplicateGroup,
    TakeoffNormalizeRequest,
    TakeoffNormalizeResponse,
)


def normalize_takeoff(payload: TakeoffNormalizeRequest) -> TakeoffNormalizeResponse:
    grouped: dict[str, list[QuantityItem]] = defaultdict(list)
    rejected: list[QuantityItem] = []
    warnings: list[str] = []

    for item in payload.items:
        reason = _rejection_reason(item, payload)
        if reason:
            rejected.append(item)
            warnings.append(f"{item.description}: {reason}")
            continue
        grouped[_dedupe_key(item)].append(item)

    normalized: list[QuantityItem] = []
    duplicate_groups: list[TakeoffDuplicateGroup] = []
    for key, items in sorted(grouped.items()):
        if payload.combine_duplicates and len(items) > 1:
            combined = _combine_items(items)
            normalized.append(combined)
            duplicate_groups.append(
                TakeoffDuplicateGroup(
                    key=key,
                    item_count=len(items),
                    combined_quantity=combined.quantity,
                    unit=combined.unit,
                    drawing_references=sorted(
                        {item.drawing_reference for item in items if item.drawing_reference}
                    ),
                )
            )
            warnings.append(f"Combined {len(items)} duplicate takeoff items for {combined.description}.")
        else:
            normalized.extend(items)

    handoff = [_to_handoff(item) for item in normalized if item.estimate_ready]
    return TakeoffNormalizeResponse(
        normalized_items=normalized,
        estimate_handoff_items=handoff,
        duplicate_groups=duplicate_groups,
        rejected_items=rejected,
        warnings=warnings,
        input_count=len(payload.items),
        normalized_count=len(normalized),
        estimate_ready_count=len(handoff),
    )


def _rejection_reason(item: QuantityItem, payload: TakeoffNormalizeRequest) -> str | None:
    if item.quantity <= 0:
        return "quantity must be greater than zero"
    if item.confidence < payload.minimum_confidence:
        return f"confidence {item.confidence:.2f} is below {payload.minimum_confidence:.2f}"
    if payload.require_drawing_reference and not item.drawing_reference:
        return "drawing reference is required"
    return None


def _dedupe_key(item: QuantityItem) -> str:
    code_or_description = (item.code or item.description).strip().lower()
    return "|".join([code_or_description, item.category, item.unit, item.revision or ""])


def _combine_items(items: list[QuantityItem]) -> QuantityItem:
    first = items[0]
    references = sorted({item.drawing_reference for item in items if item.drawing_reference})
    notes = [item.notes for item in items if item.notes]
    return first.model_copy(
        update={
            "quantity": round(sum(item.quantity for item in items), 3),
            "confidence": round(min(item.confidence for item in items), 3),
            "estimate_ready": all(item.estimate_ready for item in items),
            "drawing_reference": ", ".join(references) or None,
            "notes": "; ".join(notes) or first.notes,
        }
    )


def _to_handoff(item: QuantityItem) -> EstimateReadyItem:
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
