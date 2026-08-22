from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.customer_quote import (
    CustomerQuoteAccept,
    CustomerQuoteCreate,
    CustomerQuoteIssueStatus,
    CustomerQuoteIssueUpdate,
    CustomerQuoteList,
    CustomerQuoteRead,
    CustomerQuoteStatus,
    CustomerQuoteStatusUpdate,
    CustomerQuoteUpdate,
)
from app.services import customer_quotes
from app.services.customer_quote_pdf import render_customer_quote_pdf

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]
OptionalQuoteStatus = Annotated[CustomerQuoteStatus | None, Query()]


@router.post("", response_model=CustomerQuoteRead, status_code=status.HTTP_201_CREATED)
def create_customer_quote(
    payload: CustomerQuoteCreate,
    user: CurrentUser,
    db: DBSession,
) -> CustomerQuoteRead:
    return customer_quotes.create_customer_quote(db, payload, user.email)


@router.get("", response_model=CustomerQuoteList)
def list_customer_quotes(
    db: DBSession,
    quote_status: OptionalQuoteStatus = None,
) -> CustomerQuoteList:
    return customer_quotes.list_customer_quotes(db, quote_status=quote_status)


@router.get("/{quote_id}", response_model=CustomerQuoteRead)
def read_customer_quote(quote_id: UUID, db: DBSession) -> CustomerQuoteRead:
    return customer_quotes.get_customer_quote(db, quote_id)


@router.get("/{quote_id}/pdf")
def customer_quote_pdf(quote_id: UUID, db: DBSession) -> Response:
    quote = customer_quotes.get_customer_quote_pdf_snapshot(db, quote_id)
    return Response(
        content=render_customer_quote_pdf(quote),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{quote.quote_number}.pdf"'},
    )


@router.patch("/{quote_id}", response_model=CustomerQuoteRead)
def update_customer_quote(
    quote_id: UUID,
    payload: CustomerQuoteUpdate,
    db: DBSession,
) -> CustomerQuoteRead:
    return customer_quotes.update_customer_quote(db, quote_id, payload)


@router.post("/{quote_id}/status", response_model=CustomerQuoteRead)
def update_customer_quote_status(
    quote_id: UUID,
    payload: CustomerQuoteStatusUpdate,
    db: DBSession,
) -> CustomerQuoteRead:
    return customer_quotes.update_customer_quote_status(db, quote_id, payload)


@router.post("/{quote_id}/issue-status", response_model=CustomerQuoteRead)
def update_customer_quote_issue_status(
    quote_id: UUID,
    payload: CustomerQuoteIssueUpdate,
    user: CurrentUser,
    db: DBSession,
) -> CustomerQuoteRead:
    if payload.status in {CustomerQuoteIssueStatus.approved_for_issue, CustomerQuoteIssueStatus.issued} and user.role not in {"admin", "operations_manager"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management approval is required to approve or issue a customer quote.",
        )
    return customer_quotes.update_customer_quote_issue_status(db, quote_id, payload, user.email)


@router.post("/{quote_id}/accept", response_model=CustomerQuoteRead)
def accept_customer_quote(
    quote_id: UUID,
    payload: CustomerQuoteAccept,
    user: CurrentUser,
    db: DBSession,
) -> CustomerQuoteRead:
    if user.role not in {"admin", "operations_manager"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management approval is required to accept and award a customer quote.",
        )
    return customer_quotes.accept_customer_quote(db, quote_id, payload, user.email)
