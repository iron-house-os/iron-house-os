from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.tender import (
    TenderCreate,
    TenderIntakeCreate,
    TenderIntakeRead,
    TenderList,
    TenderRead,
    TenderUpdate,
)
from app.services import tenders

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]
OptionalStatusQuery = Annotated[str | None, Query()]


@router.post("", response_model=TenderRead, status_code=status.HTTP_201_CREATED)
def create_tender(payload: TenderCreate, db: DBSession) -> TenderRead:
    return tenders.create_tender(db, payload)


@router.post("/intake", response_model=TenderIntakeRead, status_code=status.HTTP_201_CREATED)
def intake_tender(payload: TenderIntakeCreate, db: DBSession) -> TenderIntakeRead:
    return tenders.intake_tender(db, payload)


@router.get("", response_model=TenderList)
def list_tenders(db: DBSession, status: OptionalStatusQuery = None) -> TenderList:
    return tenders.list_tenders(db, status=status)


@router.get("/{tender_id}", response_model=TenderRead)
def read_tender(tender_id: UUID, db: DBSession) -> TenderRead:
    return tenders.get_tender(db, tender_id)


@router.patch("/{tender_id}", response_model=TenderRead)
def update_tender(tender_id: UUID, payload: TenderUpdate, db: DBSession) -> TenderRead:
    return tenders.update_tender(db, tender_id, payload)
