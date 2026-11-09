from app.schemas.quote_integration import (
    QuoteComparisonLine,
    QuoteComparisonRequest,
    QuoteComparisonResponse,
    QuoteEstimateSelectionRequest,
)
from app.services.quote_selection import select_quotes_for_estimate


def compare_supplier_quotes(payload: QuoteComparisonRequest) -> QuoteComparisonResponse:
    selection = select_quotes_for_estimate(
        QuoteEstimateSelectionRequest(quotes=payload.quotes)
    )
    lines = [
        QuoteComparisonLine(
            line_item_code=decision.line_item_code,
            line_item_description=decision.line_item_description,
            scope=decision.scope,
            scope_type=decision.scope_type,
            lowest_supplier=decision.lowest_qualified_supplier,
            lowest_amount=decision.lowest_qualified_amount,
            selected_supplier=decision.selected_supplier,
            selected_amount=decision.selected_amount,
            selected_is_lowest=decision.selected_is_lowest,
            selection_reason=decision.selection_reason,
            quote_count=decision.quote_count,
            qualified_quote_count=decision.qualified_quote_count,
            ready_for_estimate=decision.ready_for_estimate,
            blockers=decision.blockers,
        )
        for decision in selection.decisions
    ]
    total_lowest = sum(line.lowest_amount or 0 for line in lines)
    total_selected = sum(line.selected_amount or 0 for line in lines)
    return QuoteComparisonResponse(
        lines=lines,
        total_lowest=round(total_lowest, 2),
        total_selected=round(total_selected, 2),
        delta_from_lowest=round(total_selected - total_lowest, 2),
        ready_for_estimate=selection.ready_for_estimate,
        blockers=selection.blockers,
    )
