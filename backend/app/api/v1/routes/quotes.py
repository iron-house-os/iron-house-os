from fastapi import APIRouter

from app.schemas.quote_integration import QuoteComparisonRequest, QuoteComparisonResponse
from app.services.quote_comparison import compare_supplier_quotes

router = APIRouter()


@router.post("/compare", response_model=QuoteComparisonResponse)
def compare_quotes(payload: QuoteComparisonRequest) -> QuoteComparisonResponse:
    return compare_supplier_quotes(payload)
