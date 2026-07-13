from app.schemas.quote_integration import (
    QuoteComparisonRequest,
    QuoteEstimateSelectionRequest,
    QuoteStatus,
    SupplierQuoteCreate,
)
from app.services.quote_comparison import compare_supplier_quotes
from app.services.quote_selection import select_quotes_for_estimate


def quote(
    supplier: str,
    amount: float,
    *,
    selected: bool = False,
    reason: str | None = None,
    qualified: bool = True,
    status: QuoteStatus = QuoteStatus.received,
    revision: int = 1,
) -> SupplierQuoteCreate:
    return SupplierQuoteCreate(
        supplier_name=supplier,
        quote_reference="Q-PIPE",
        revision=revision,
        line_item_code="PIPE-001",
        line_item_description="PVC storm pipe supply",
        scope="Supply PVC storm pipe",
        amount=amount,
        is_qualified=qualified,
        status=status,
        is_selected=selected,
        selection_reason=reason,
    )


def test_automatically_selects_lowest_received_qualified_quote() -> None:
    quotes = [
        quote("Unqualified low", 8000, qualified=False),
        quote("Bounced low", 8500, status=QuoteStatus.bounced),
        quote("Qualified A", 10000),
        quote("Qualified B", 9500),
    ]

    result = select_quotes_for_estimate(
        QuoteEstimateSelectionRequest(quotes=quotes)
    )

    assert result.ready_for_estimate is True
    assert result.blockers == []
    assert result.decisions[0].lowest_qualified_supplier == "Qualified B"
    assert result.decisions[0].selected_supplier == "Qualified B"
    assert result.decisions[0].qualified_quote_count == 2
    assert result.line_items[0].vendor_quotes[0].supplier == "Qualified B"
    assert result.line_items[0].vendor_quotes[0].is_selected is True


def test_preserves_documented_non_low_selection_in_estimate_line_item() -> None:
    quotes = [
        quote("Lowest", 10000),
        quote(
            "Preferred supplier",
            11250,
            selected=True,
            reason="Complete scope and confirmed delivery",
        ),
    ]

    result = select_quotes_for_estimate(
        QuoteEstimateSelectionRequest(quotes=quotes)
    )

    decision = result.decisions[0]
    selected_quote = result.line_items[0].vendor_quotes[0]
    assert result.ready_for_estimate is True
    assert decision.selected_supplier == "Preferred supplier"
    assert decision.selected_is_lowest is False
    assert decision.selection_reason == "Complete scope and confirmed delivery"
    assert selected_quote.is_selected is True
    assert selected_quote.selection_reason == "Complete scope and confirmed delivery"


def test_blocks_non_low_selection_without_reason() -> None:
    result = select_quotes_for_estimate(
        QuoteEstimateSelectionRequest(
            quotes=[
                quote("Lowest", 10000),
                quote("Undocumented choice", 11250, selected=True),
            ]
        )
    )

    assert result.ready_for_estimate is False
    assert result.line_items == []
    assert "explain why Undocumented choice is selected" in result.blockers[0]


def test_blocks_multiple_manual_selections() -> None:
    result = select_quotes_for_estimate(
        QuoteEstimateSelectionRequest(
            quotes=[
                quote("Supplier A", 10000, selected=True),
                quote("Supplier B", 10500, selected=True),
            ]
        )
    )

    assert result.ready_for_estimate is False
    assert result.line_items == []
    assert "multiple quotes are selected" in result.blockers[0]


def test_uses_latest_supplier_quote_revision_and_comparison_policy() -> None:
    quotes = [
        quote("Revised supplier", 8000, revision=1),
        quote("Revised supplier", 12000, revision=2),
        quote("Current lowest", 11000),
    ]

    selection = select_quotes_for_estimate(
        QuoteEstimateSelectionRequest(quotes=quotes)
    )
    comparison = compare_supplier_quotes(QuoteComparisonRequest(quotes=quotes))

    assert selection.decisions[0].quote_count == 2
    assert selection.decisions[0].selected_supplier == "Current lowest"
    assert comparison.ready_for_estimate is True
    assert comparison.total_lowest == 11000
    assert comparison.total_selected == 11000


def test_empty_quote_set_is_not_ready_for_estimate() -> None:
    result = select_quotes_for_estimate(QuoteEstimateSelectionRequest())

    assert result.ready_for_estimate is False
    assert result.line_items == []
    assert result.blockers == [
        "Add at least one supplier quote before sending pricing to the estimate."
    ]
