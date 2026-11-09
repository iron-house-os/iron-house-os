from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.employee_onboarding import PortalOnboardingRead, PortalProgressUpdate, PortalSubmission
from app.services import employee_onboarding as service
from app.services.onboarding_data import OnboardingDataUnavailable

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _resolve_or_404(db: Session, token: str):
    record = service.resolve_token(db, token)
    if record is None:
        raise HTTPException(status_code=404, detail="Invitation is invalid, revoked, or expired.")
    return record


def _portal_read(record) -> PortalOnboardingRead:
    try:
        return service.portal_read(record)
    except OnboardingDataUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="Restricted onboarding data is unavailable. Contact an administrator.",
        ) from exc


@router.get("/{token}", response_model=PortalOnboardingRead)
def portal_record(token: str, db: DBSession) -> PortalOnboardingRead:
    record = _resolve_or_404(db, token)
    if record.status in {"invitation_ready", "invitation_sent"}:
        record.status = "invitation_opened"
        service.audit(db, record, "invitation_opened", record.personal_email)
        db.commit()
        db.refresh(record)
    return _portal_read(record)


@router.put("/{token}/progress", response_model=PortalOnboardingRead)
def save_progress(token: str, payload: PortalProgressUpdate, db: DBSession) -> PortalOnboardingRead:
    try:
        record = service.update_progress(db, _resolve_or_404(db, token), payload.packet)
        return _portal_read(record)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{token}/submit", response_model=PortalOnboardingRead)
def submit(token: str, payload: PortalSubmission, db: DBSession) -> PortalOnboardingRead:
    try:
        record = service.submit(
            db,
            _resolve_or_404(db, token),
            payload.packet,
            payload.acknowledgement,
            payload.signature_name,
        )
        return _portal_read(record)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
