from __future__ import annotations

from collections import defaultdict

from app.schemas.quote_integration import (
    QuoteComparisonLine,
    QuoteComparisonRequest,
    QuoteComparisonResponse,
    SupplierQuoteCreate,
)


def compare_supplier_quotes(payload: QuoteComparisonRequest) -> QuoteComparisonResponse:
    grouped_quotes: dict[tuple[str | None, str, str], list[SupplierQuoteCreate]] = defaultdict(list)
    for quote in payload.quotes:
        key = (quote.line_item_code, quote.line_item_description or quote.scope, quote.scope)
        grouped_quotes[key].append(quote)

    lines: list[QuoteComparisonLine] = []
    total_lowest = 0.0
    total_selected = 0.0

    for (line_item_code, line_item_description, scope), quotes in grouped_quotes.items():
        lowest_quote = min(quotes, key=lambda quote: quote.amount)
        selected_quotes = [quote for quote in quotes if quote.is_selected]
        selected_quote = min(selected_quotes, key=lambda quote: quote.amount) if selected_quotes else lowest_quote
        selected_is_lowest = selected_quote.amount == lowest_quote.amount

        total_lowest += lowest_quote.amount
        total_selected += selected_quote.amount
        lines.append(
            QuoteComparisonLine(
                line_item_code=line_item_code,
                line_item_description=line_item_description,
                scope=scope,
                lowest_supplier=lowest_quote.supplier_name,
                lowest_amount=round(lowest_quote.amount, 2),
                selected_supplier=selected_quote.supplier_name,
                selected_amount=round(selected_quote.amount, 2),
                selected_is_lowest=selected_is_lowest,
                selection_reason=selected_quote.selection_reason,
                quote_count=len(quotes),
            )
        )

    return QuoteComparisonResponse(
        lines=lines,
        total_lowest=round(total_lowest, 2),
        total_selected=round(total_selected, 2),
        delta_from_lowest=round(total_selected - total_lowest, 2),
    )
