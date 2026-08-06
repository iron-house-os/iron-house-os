from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.employee_onboarding import EmployeeOnboardingRead, PortalProgressUpdate, PortalSubmission
from app.services import employee_onboarding as service

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _resolve_or_404(db: Session, token: str):
    record = service.resolve_token(db, token)
    if record is None:
        raise HTTPException(status_code=404, detail="Invitation is invalid, revoked, or expired.")
    return record


@router.get("/{token}", response_model=EmployeeOnboardingRead)
def portal_record(token: str, db: DBSession) -> EmployeeOnboardingRead:
    record = _resolve_or_404(db, token)
    if record.status == "invitation_sent":
        record.status = "invitation_opened"
        service.audit(db, record, "invitation_opened", record.personal_email)
        db.commit()
        db.refresh(record)
    return EmployeeOnboardingRead.model_validate(record)


@router.put("/{token}/progress", response_model=EmployeeOnboardingRead)
def save_progress(token: str, payload: PortalProgressUpdate, db: DBSession) -> EmployeeOnboardingRead:
    return EmployeeOnboardingRead.model_validate(service.update_progress(db, _resolve_or_404(db, token), payload.completed_items))


@router.post("/{token}/submit", response_model=EmployeeOnboardingRead)
def submit(token: str, payload: PortalSubmission, db: DBSession) -> EmployeeOnboardingRead:
    try:
        return EmployeeOnboardingRead.model_validate(
            service.submit(db, _resolve_or_404(db, token), payload.completed_items, payload.acknowledgement)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
