from fastapi import APIRouter

from app.schemas.quote_integration import (
    QuoteComparisonRequest,
    QuoteComparisonResponse,
    QuoteEstimateImportRequest,
    QuoteEstimateImportResponse,
    QuoteEstimateSelectionRequest,
    QuoteEstimateSelectionResponse,
)
from app.services.quote_comparison import compare_supplier_quotes
from app.services.quote_estimate import import_quotes_to_estimate
from app.services.quote_selection import select_quotes_for_estimate

router = APIRouter()


@router.post("/compare", response_model=QuoteComparisonResponse)
def compare_quotes(payload: QuoteComparisonRequest) -> QuoteComparisonResponse:
    return compare_supplier_quotes(payload)


@router.post("/estimate-selection", response_model=QuoteEstimateSelectionResponse)
def select_quote_pricing(
    payload: QuoteEstimateSelectionRequest,
) -> QuoteEstimateSelectionResponse:
    return select_quotes_for_estimate(payload)


@router.post("/estimate-import", response_model=QuoteEstimateImportResponse)
def import_quote_pricing(payload: QuoteEstimateImportRequest) -> QuoteEstimateImportResponse:
    return import_quotes_to_estimate(payload)
