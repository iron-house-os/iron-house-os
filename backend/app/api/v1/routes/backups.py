from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.backups import (
    BackupsControllerResult,
    BackupsIntakeCreate,
    BackupsIntakeList,
    BackupsIntakeRead,
)
from app.services import backups

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=BackupsIntakeRead, status_code=status.HTTP_201_CREATED)
def create_intake(
    payload: BackupsIntakeCreate,
    user: CurrentUser,
    db: DBSession,
) -> BackupsIntakeRead:
    return backups.create_intake(db, payload, user)


@router.get("", response_model=BackupsIntakeList)
def list_intakes(user: CurrentUser, db: DBSession) -> BackupsIntakeList:
    return backups.list_intakes(db, user)


@router.get("/{intake_id}", response_model=BackupsIntakeRead)
def read_intake(intake_id: UUID, user: CurrentUser, db: DBSession) -> BackupsIntakeRead:
    return backups.get_intake(db, intake_id, user)


@router.post("/{intake_id}/retry", response_model=BackupsIntakeRead)
def retry_intake(intake_id: UUID, user: CurrentUser, db: DBSession) -> BackupsIntakeRead:
    return backups.retry_intake(db, intake_id, user)


@router.post("/controller/daily", response_model=BackupsControllerResult)
def run_daily_controller(
    user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=500),
) -> BackupsControllerResult:
    return backups.run_daily_controller_for_user(db, user, limit=limit)
