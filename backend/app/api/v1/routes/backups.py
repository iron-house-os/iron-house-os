from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.core.errors import AppError
from app.schemas.backups import (
    BackupControllerRunRead,
    BackupIntakeList,
    BackupIntakeRead,
    BackupRetryRequest,
)
from app.services import backups

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=BackupIntakeRead, status_code=status.HTTP_201_CREATED)
async def upload_backup(
    user: CurrentUser,
    db: DBSession,
    file: list[UploadFile] = File(...),
    note: str | None = Form(default=None),
    project_hint: str | None = Form(default=None),
) -> BackupIntakeRead:
    if len(file) != 1:
        raise AppError("Backups accepts exactly one image.", status_code=422)
    return await backups.create_intake(db, file[0], note=note, project_hint=project_hint, user=user)


@router.get("", response_model=BackupIntakeList)
def list_backups(user: CurrentUser, db: DBSession) -> BackupIntakeList:
    return backups.list_intakes(db, user)


@router.get("/{intake_id}", response_model=BackupIntakeRead)
def read_backup(intake_id: UUID, user: CurrentUser, db: DBSession) -> BackupIntakeRead:
    return backups.get_intake(db, intake_id, user)


@router.post("/{intake_id}/retry", response_model=BackupIntakeRead)
def retry_backup(
    intake_id: UUID,
    payload: BackupRetryRequest,
    user: CurrentUser,
    db: DBSession,
) -> BackupIntakeRead:
    return backups.retry_intake(db, intake_id, payload.reason, user)


@router.post("/controller/daily", response_model=BackupControllerRunRead)
def run_daily_controller(user: CurrentUser, db: DBSession) -> BackupControllerRunRead:
    backups._require_management(user)
    return backups.run_daily_controller(db)
