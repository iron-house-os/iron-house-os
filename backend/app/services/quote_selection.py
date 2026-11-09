from __future__ import annotations

from collections import defaultdict

from app.schemas.estimate import (
    EstimateItemType,
    EstimateLineItem,
    EstimateUnit,
    VendorQuoteInput,
)
from app.schemas.quote_integration import (
    QuoteEstimateSelectionRequest,
    QuoteEstimateSelectionResponse,
    QuoteScopeType,
    QuoteSelectionDecision,
    QuoteStatus,
    SupplierQuoteCreate,
)


def select_quotes_for_estimate(
    payload: QuoteEstimateSelectionRequest,
) -> QuoteEstimateSelectionResponse:
    quotes = _select_current_revisions(payload.quotes)
    grouped: dict[tuple[str, str], list[SupplierQuoteCreate]] = defaultdict(list)
    for quote in quotes:
        grouped[_line_item_key(quote)].append(quote)

    if not grouped:
        blocker = "Add at least one supplier quote before sending pricing to the estimate."
        return QuoteEstimateSelectionResponse(
            decisions=[],
            line_items=[],
            ready_for_estimate=False,
            blockers=[blocker],
        )

    decisions: list[QuoteSelectionDecision] = []
    line_items: list[EstimateLineItem] = []
    blockers: list[str] = []

    for key in sorted(grouped):
        decision, line_item = _evaluate_group(grouped[key])
        decisions.append(decision)
        blockers.extend(decision.blockers)
        if line_item is not None:
            line_items.append(line_item)

    return QuoteEstimateSelectionResponse(
        decisions=decisions,
        line_items=line_items,
        ready_for_estimate=not blockers and len(line_items) == len(decisions),
        blockers=blockers,
    )


def _evaluate_group(
    quotes: list[SupplierQuoteCreate],
) -> tuple[QuoteSelectionDecision, EstimateLineItem | None]:
    first = quotes[0]
    label = first.line_item_code or first.line_item_description or first.scope
    eligible = [quote for quote in quotes if _is_eligible(quote)]
    eligible.sort(key=lambda quote: (quote.amount, quote.supplier_name.casefold()))
    lowest = eligible[0] if eligible else None

    manually_selected = [
        quote
        for quote in quotes
        if quote.is_selected or quote.status == QuoteStatus.selected
    ]
    blockers: list[str] = []
    selected: SupplierQuoteCreate | None = None

    if not eligible:
        blockers.append(
            f"{label}: no received, positive, qualified supplier quote is available."
        )

    if len(manually_selected) > 1:
        suppliers = ", ".join(quote.supplier_name for quote in manually_selected)
        blockers.append(
            f"{label}: select exactly one supplier; multiple quotes are selected ({suppliers})."
        )
    elif len(manually_selected) == 1:
        candidate = manually_selected[0]
        if not _is_eligible(candidate):
            reasons = _ineligible_reasons(candidate)
            blockers.append(
                f"{label}: selected quote from {candidate.supplier_name} is not eligible "
                f"({'; '.join(reasons)})."
            )
        else:
            selected = candidate
    else:
        selected = lowest

    selected_is_lowest = (
        selected is None
        or lowest is None
        or selected.amount == lowest.amount
    )
    selection_reason = (
        selected.selection_reason.strip()
        if selected and selected.selection_reason and selected.selection_reason.strip()
        else None
    )
    if selected and not selected_is_lowest and not selection_reason:
        blockers.append(
            f"{label}: explain why {selected.supplier_name} is selected over the "
            f"lowest qualified quote from {lowest.supplier_name}."
        )

    ready = selected is not None and not blockers
    source = selected or lowest or first
    decision = QuoteSelectionDecision(
        line_item_code=source.line_item_code,
        line_item_description=source.line_item_description or source.scope,
        scope=source.scope,
        scope_type=source.scope_type,
        lowest_qualified_supplier=lowest.supplier_name if lowest else None,
        lowest_qualified_amount=round(lowest.amount, 2) if lowest else None,
        selected_supplier=selected.supplier_name if selected else None,
        selected_amount=round(selected.amount, 2) if selected else None,
        selected_is_lowest=selected_is_lowest,
        selection_reason=selection_reason,
        quote_count=len(quotes),
        qualified_quote_count=len(eligible),
        ready_for_estimate=ready,
        blockers=blockers,
    )
    if not ready or selected is None:
        return decision, None

    ordered_quotes = sorted(
        eligible,
        key=lambda quote: (
            quote is not selected,
            quote.amount,
            quote.supplier_name.casefold(),
        ),
    )
    vendor_quotes = [
        VendorQuoteInput(
            supplier=quote.supplier_name,
            scope=quote.scope,
            amount=quote.amount,
            is_qualified=quote.is_qualified,
            qualification_notes=quote.qualification_notes,
            is_selected=quote is selected,
            selection_reason=(
                quote.selection_reason.strip()
                if quote.selection_reason and quote.selection_reason.strip()
                else None
            ),
            notes=quote.notes,
        )
        for quote in ordered_quotes
    ]
    line_item = EstimateLineItem(
        code=selected.line_item_code,
        description=selected.line_item_description or selected.scope,
        item_type=(
            EstimateItemType.material
            if selected.scope_type == QuoteScopeType.material
            else EstimateItemType.subcontract
        ),
        quantity=1,
        unit=EstimateUnit.lump_sum,
        vendor_quotes=vendor_quotes,
        notes=(
            f"Supplier selection: {selection_reason}"
            if selection_reason
            else "Lowest qualified supplier quote selected."
        ),
    )
    return decision, line_item


def _line_item_key(quote: SupplierQuoteCreate) -> tuple[str, str]:
    code = (quote.line_item_code or "").strip().casefold()
    if code:
        return ("code", code)
    description = (quote.line_item_description or quote.scope).strip().casefold()
    return ("description", description)


def _revision_key(quote: SupplierQuoteCreate) -> tuple[str, str, str, str]:
    line_key = _line_item_key(quote)
    return (
        quote.supplier_name.strip().casefold(),
        (quote.quote_reference or "").strip().casefold(),
        f"{line_key[0]}:{line_key[1]}",
        quote.scope.strip().casefold(),
    )


def _select_current_revisions(
    quotes: list[SupplierQuoteCreate],
) -> list[SupplierQuoteCreate]:
    current: dict[tuple[str, str, str, str], SupplierQuoteCreate] = {}
    for quote in quotes:
        key = _revision_key(quote)
        existing = current.get(key)
        if existing is None or quote.revision >= existing.revision:
            current[key] = quote
    return list(current.values())


def _is_eligible(quote: SupplierQuoteCreate) -> bool:
    return (
        quote.is_qualified
        and quote.status in {QuoteStatus.received, QuoteStatus.selected}
        and quote.amount > 0
    )


def _ineligible_reasons(quote: SupplierQuoteCreate) -> list[str]:
    reasons: list[str] = []
    if not quote.is_qualified:
        reasons.append("not qualified")
    if quote.status not in {QuoteStatus.received, QuoteStatus.selected}:
        reasons.append(f"status is {quote.status.value}")
    if quote.amount <= 0:
        reasons.append("amount must be greater than zero")
    return reasons
