from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.takeoff import QuantityRegisterRequest, QuantityRegisterResponse, TakeoffEngineRequest, TakeoffEngineResponse
from app.schemas.takeoff_persistence import TakeoffList, TakeoffRead, TakeoffSaveRequest
from app.services import takeoff_persistence
from app.services.takeoff import run_takeoff_engine, summarize_quantity_register

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("/summarize", response_model=QuantityRegisterResponse)
def summarize(payload: QuantityRegisterRequest) -> QuantityRegisterResponse:
    return summarize_quantity_register(payload)


@router.post("/engine", response_model=TakeoffEngineResponse)
def engine(payload: TakeoffEngineRequest) -> TakeoffEngineResponse:
    return run_takeoff_engine(payload)


@router.post("/save", response_model=TakeoffRead, status_code=status.HTTP_201_CREATED)
def save(payload: TakeoffSaveRequest, db: DBSession) -> TakeoffRead:
    return takeoff_persistence.save_takeoff(db, payload)


@router.get("/project/{project_id}", response_model=TakeoffList)
def list_for_project(project_id: UUID, db: DBSession) -> TakeoffList:
    return takeoff_persistence.list_project_takeoffs(db, project_id)


@router.get("/{takeoff_id}", response_model=TakeoffRead)
def read(takeoff_id: UUID, db: DBSession) -> TakeoffRead:
    return takeoff_persistence.get_takeoff(db, takeoff_id)
