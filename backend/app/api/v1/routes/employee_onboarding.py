from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AdminUser
from app.db.session import get_db
from app.schemas.employee_onboarding import (
    CorrectionRequest,
    EmployeeOnboardingCreate,
    EmployeeOnboardingList,
    EmployeeOnboardingRead,
    InvitationRead,
    POSITION_OPTIONS,
    PortalProgressUpdate,
    PortalSubmission,
    PositionOption,
)
from app.services import employee_onboarding as service

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _record_or_404(db: Session, onboarding_id: UUID):
    record = service.get(db, onboarding_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Employee onboarding record not found.")
    return record


@router.get("/positions", response_model=list[PositionOption])
def positions(_: AdminUser) -> list[PositionOption]:
    return POSITION_OPTIONS


@router.get("", response_model=EmployeeOnboardingList)
def list_onboarding(_: AdminUser, db: DBSession) -> EmployeeOnboardingList:
    items = service.list_records(db)
    return EmployeeOnboardingList(items=[EmployeeOnboardingRead.model_validate(item) for item in items], total=len(items))


@router.post("", response_model=EmployeeOnboardingRead, status_code=status.HTTP_201_CREATED)
def create_onboarding(payload: EmployeeOnboardingCreate, admin: AdminUser, db: DBSession) -> EmployeeOnboardingRead:
    return EmployeeOnboardingRead.model_validate(service.create(db, payload, admin.email))


@router.post("/{onboarding_id}/invite", response_model=InvitationRead)
def invite(onboarding_id: UUID, request: Request, admin: AdminUser, db: DBSession) -> InvitationRead:
    record = _record_or_404(db, onboarding_id)
    token, expires_at = service.issue_invitation(db, record, admin.email)
    base_url = str(request.base_url).rstrip("/")
    return InvitationRead(onboarding_id=record.id, invite_url=f"{base_url}/employee-onboarding/{token}", expires_at=expires_at)


@router.post("/{onboarding_id}/revoke", response_model=EmployeeOnboardingRead)
def revoke(onboarding_id: UUID, admin: AdminUser, db: DBSession) -> EmployeeOnboardingRead:
    record = _record_or_404(db, onboarding_id)
    record.invitation_revoked_at = service.utcnow()
    record.status = "cancelled"
    service.audit(db, record, "invitation_revoked", admin.email)
    db.commit()
    db.refresh(record)
    return EmployeeOnboardingRead.model_validate(record)


@router.post("/{onboarding_id}/request-corrections", response_model=EmployeeOnboardingRead)
def request_corrections(onboarding_id: UUID, payload: CorrectionRequest, admin: AdminUser, db: DBSession) -> EmployeeOnboardingRead:
    record = _record_or_404(db, onboarding_id)
    if record.status != "submitted":
        raise HTTPException(status_code=409, detail="Only submitted onboarding can be returned for corrections.")
    record.status = "corrections_required"
    record.correction_note = payload.note
    service.audit(db, record, "corrections_requested", admin.email)
    db.commit()
    db.refresh(record)
    return EmployeeOnboardingRead.model_validate(record)


@router.post("/{onboarding_id}/approve", response_model=EmployeeOnboardingRead)
def approve(onboarding_id: UUID, admin: AdminUser, db: DBSession) -> EmployeeOnboardingRead:
    record = _record_or_404(db, onboarding_id)
    if record.status != "submitted":
        raise HTTPException(status_code=409, detail="Only submitted onboarding can be approved.")
    record.status = "approved"
    record.approved_at = service.utcnow()
    record.reviewer_id = admin.id
    service.audit(db, record, "approved", admin.email)
    db.commit()
    db.refresh(record)
    return EmployeeOnboardingRead.model_validate(record)


@router.post("/{onboarding_id}/activate", response_model=EmployeeOnboardingRead)
def activate(onboarding_id: UUID, admin: AdminUser, db: DBSession) -> EmployeeOnboardingRead:
    try:
        return EmployeeOnboardingRead.model_validate(service.activate(db, _record_or_404(db, onboarding_id), admin.email))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/portal/{token}", response_model=EmployeeOnboardingRead)
def portal_record(token: str, db: DBSession) -> EmployeeOnboardingRead:
    record = service.resolve_token(db, token)
    if record is None:
        raise HTTPException(status_code=404, detail="Invitation is invalid, revoked, or expired.")
    if record.status == "invitation_sent":
        record.status = "invitation_opened"
        service.audit(db, record, "invitation_opened", record.personal_email)
        db.commit()
        db.refresh(record)
    return EmployeeOnboardingRead.model_validate(record)


@router.put("/portal/{token}/progress", response_model=EmployeeOnboardingRead)
def save_progress(token: str, payload: PortalProgressUpdate, db: DBSession) -> EmployeeOnboardingRead:
    record = service.resolve_token(db, token)
    if record is None:
        raise HTTPException(status_code=404, detail="Invitation is invalid, revoked, or expired.")
    return EmployeeOnboardingRead.model_validate(service.update_progress(db, record, payload.completed_items))


@router.post("/portal/{token}/submit", response_model=EmployeeOnboardingRead)
def submit(token: str, payload: PortalSubmission, db: DBSession) -> EmployeeOnboardingRead:
    record = service.resolve_token(db, token)
    if record is None:
        raise HTTPException(status_code=404, detail="Invitation is invalid, revoked, or expired.")
    try:
        return EmployeeOnboardingRead.model_validate(service.submit(db, record, payload.completed_items, payload.acknowledgement))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
