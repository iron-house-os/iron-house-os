from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.field_operations import (
    CertificationCreate,
    CertificationRead,
    EmployeeCreate,
    EmployeeRead,
    FieldOperationsBootstrap,
    FieldRecordCreate,
    FieldRecordRead,
    MilestoneDecision,
    SignatureCreate,
    TimeEntryCreate,
    TimeEntryRead,
    TimeOffDecision,
    VehicleCreate,
    VehicleLogCreate,
    VehicleLogRead,
    VehicleRead,
    VehicleUpdate,
)
from app.services import field_operations

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.get("/bootstrap", response_model=FieldOperationsBootstrap)
def bootstrap(db: DBSession, user: CurrentUser) -> FieldOperationsBootstrap:
    return field_operations.get_bootstrap(db, user)


@router.post("/employees", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: DBSession, user: CurrentUser) -> EmployeeRead:
    return field_operations.create_employee(db, payload, user)


@router.post("/certifications", response_model=CertificationRead, status_code=status.HTTP_201_CREATED)
def create_certification(payload: CertificationCreate, db: DBSession) -> CertificationRead:
    return field_operations.create_certification(db, payload)


@router.post("/vehicles", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, db: DBSession) -> VehicleRead:
    return field_operations.create_vehicle(db, payload)


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(vehicle_id: UUID, payload: VehicleUpdate, db: DBSession) -> VehicleRead:
    return field_operations.update_vehicle(db, vehicle_id, payload)


@router.post("/vehicle-logs", response_model=VehicleLogRead, status_code=status.HTTP_201_CREATED)
def create_vehicle_log(payload: VehicleLogCreate, db: DBSession) -> VehicleLogRead:
    return field_operations.create_vehicle_log(db, payload)


@router.post("/time-entries", response_model=TimeEntryRead, status_code=status.HTTP_201_CREATED)
def create_time_entry(payload: TimeEntryCreate, db: DBSession, user: CurrentUser) -> TimeEntryRead:
    return field_operations.create_time_entry(db, payload, user)


@router.post("/records", response_model=FieldRecordRead, status_code=status.HTTP_201_CREATED)
def create_field_record(payload: FieldRecordCreate, db: DBSession, user: CurrentUser) -> FieldRecordRead:
    return field_operations.create_field_record(db, payload, user)


@router.post("/records/{record_id}/sign", response_model=FieldRecordRead)
def sign_field_record(
    record_id: UUID,
    payload: SignatureCreate,
    db: DBSession,
    user: CurrentUser,
) -> FieldRecordRead:
    return field_operations.sign_field_record(db, record_id, payload, user)


@router.post("/records/{record_id}/milestone-decision", response_model=FieldRecordRead)
def decide_milestone(
    record_id: UUID,
    payload: MilestoneDecision,
    db: DBSession,
    user: CurrentUser,
) -> FieldRecordRead:
    return field_operations.decide_milestone(db, record_id, payload, user)


@router.post("/records/{record_id}/time-off-decision", response_model=FieldRecordRead)
def decide_time_off(
    record_id: UUID,
    payload: TimeOffDecision,
    db: DBSession,
    user: CurrentUser,
) -> FieldRecordRead:
    return field_operations.decide_time_off(db, record_id, payload, user)
