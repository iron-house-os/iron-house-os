from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.quote_integration import (
    QuoteComparisonRequest,
    QuoteComparisonResponse,
    QuoteEstimateImportRequest,
    QuoteEstimateImportResponse,
    QuoteEstimateSelectionRequest,
    QuoteEstimateSelectionResponse,
    SupplierQuoteList,
    SupplierQuoteRead,
    SupplierQuoteRecordCreate,
    SupplierQuoteUpdate,
)
from app.services.quote_comparison import compare_supplier_quotes
from app.services.quote_estimate import import_quotes_to_estimate
from app.services.quote_selection import select_quotes_for_estimate
from app.services import quotes

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=SupplierQuoteList)
def list_project_quotes(project_id: UUID, db: DBSession) -> SupplierQuoteList:
    items = quotes.list_quotes(db, project_id)
    return SupplierQuoteList(items=items, total=len(items))


@router.post("", response_model=SupplierQuoteRead, status_code=status.HTTP_201_CREATED)
def create_project_quote(
    payload: SupplierQuoteRecordCreate,
    db: DBSession,
) -> SupplierQuoteRead:
    return quotes.create_quote(db, payload)


@router.patch("/{quote_id}", response_model=SupplierQuoteRead)
def update_project_quote(
    quote_id: UUID,
    payload: SupplierQuoteUpdate,
    db: DBSession,
) -> SupplierQuoteRead:
    return quotes.update_quote(db, quote_id, payload)


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
