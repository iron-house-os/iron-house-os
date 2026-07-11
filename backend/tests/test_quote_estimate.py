from app.schemas.quote_integration import (
    QuoteEstimateImportRequest,
    QuoteScopeType,
    SupplierQuoteCreate,
)
from app.services.quote_estimate import import_quotes_to_estimate


def test_quote_import_maps_scope_to_cost_code() -> None:
    result = import_quotes_to_estimate(
        QuoteEstimateImportRequest(
            quotes=[
                SupplierQuoteCreate(
                    supplier_name="EMCO",
                    quote_reference="Q-100",
                    scope="PVC storm pipe supply",
                    scope_type=QuoteScopeType.material,
                    amount=12500,
                )
            ]
        )
    )

    assert result.mapped_count == 1
    assert result.review_count == 0
    assert result.lines[0].cost_code == "03-100"
    assert result.total_amount == 12500


def test_quote_import_keeps_latest_revision_only_by_default() -> None:
    result = import_quotes_to_estimate(
        QuoteEstimateImportRequest(
            quotes=[
                SupplierQuoteCreate(
                    supplier_name="Superior Paving",
                    quote_reference="SP-22",
                    revision=1,
                    scope="Asphalt paving",
                    scope_type=QuoteScopeType.subcontract,
                    amount=40000,
                ),
                SupplierQuoteCreate(
                    supplier_name="Superior Paving",
                    quote_reference="SP-22",
                    revision=2,
                    scope="Asphalt paving",
                    scope_type=QuoteScopeType.subcontract,
                    amount=38500,
                ),
            ]
        )
    )

    assert len(result.lines) == 1
    assert result.lines[0].revision == 2
    assert result.total_amount == 38500
    assert result.revisions[0].superseded_revisions == [1]


def test_quote_import_flags_unmapped_and_zero_pricing() -> None:
    result = import_quotes_to_estimate(
        QuoteEstimateImportRequest(
            quotes=[
                SupplierQuoteCreate(
                    supplier_name="Unknown Supplier",
                    scope="Special proprietary item xyz",
                    amount=0,
                )
            ]
        )
    )

    assert result.review_count == 1
    assert result.lines[0].needs_review is True
    assert result.lines[0].cost_code is None
    assert any("zero amount" in warning for warning in result.warnings)


def test_quote_import_preserves_exclusion_warning() -> None:
    result = import_quotes_to_estimate(
        QuoteEstimateImportRequest(
            quotes=[
                SupplierQuoteCreate(
                    supplier_name="JWS",
                    scope="Concrete sidewalk",
                    scope_type=QuoteScopeType.subcontract,
                    amount=21000,
                    exclusions=["Winter heat", "Traffic control"],
                )
            ]
        )
    )

    assert result.lines[0].cost_code == "04-200"
    assert result.lines[0].exclusions == ["Winter heat", "Traffic control"]
    assert any("2 exclusion" in warning for warning in result.warnings)
