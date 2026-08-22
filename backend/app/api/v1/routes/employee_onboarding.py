import csv
import io
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AdminUser, CurrentUser
from app.db.session import get_db
from app.schemas.employee_onboarding import (
    CorrectionRequest,
    DeploymentStatusRead,
    EmployeeOnboardingCreate,
    EmployeeOnboardingList,
    EmployeeOnboardingRead,
    InvitationRead,
    POSITION_OPTIONS,
    PortalActivationRead,
    PortalPacket,
    PositionOption,
    WorkerOrientationCreate,
    WorkerOrientationRead,
)
from app.services import employee_onboarding as service
from app.services.onboarding_data import OnboardingDataUnavailable

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _require_management(user: CurrentUser):
    if user.role not in {"admin", "operations_manager"}:
        raise HTTPException(status_code=403, detail="Management access is required.")
    return user


def _record_or_404(db: Session, onboarding_id: UUID):
    record = service.get(db, onboarding_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Employee onboarding record not found.")
    return record


@router.get("/positions", response_model=list[PositionOption])
def positions(_: AdminUser) -> list[PositionOption]:
    return POSITION_OPTIONS


@router.get("", response_model=EmployeeOnboardingList)
def list_onboarding(user: CurrentUser, db: DBSession) -> EmployeeOnboardingList:
    _require_management(user)
    items = service.list_records(db)
    return EmployeeOnboardingList(items=[EmployeeOnboardingRead.model_validate(item) for item in items], total=len(items))


@router.post("", response_model=EmployeeOnboardingRead, status_code=status.HTTP_201_CREATED)
def create_onboarding(payload: EmployeeOnboardingCreate, admin: AdminUser, db: DBSession) -> EmployeeOnboardingRead:
    return EmployeeOnboardingRead.model_validate(service.create(db, payload, admin.email))


@router.post("/{onboarding_id}/invite", response_model=InvitationRead)
def invite(onboarding_id: UUID, request: Request, admin: AdminUser, db: DBSession) -> InvitationRead:
    record = _record_or_404(db, onboarding_id)
    try:
        token, expires_at = service.issue_invitation(db, record, admin.email)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    base_url = str(request.base_url).rstrip("/")
    invite_url = f"{base_url}/employee-onboarding/{token}"
    delivery_status = service.deliver_invitation(
        db,
        record,
        invite_url=invite_url,
        actor=admin.email,
    )
    return InvitationRead(
        onboarding_id=record.id,
        invite_url=invite_url,
        expires_at=expires_at,
        delivery_status=delivery_status,
    )


@router.post("/{onboarding_id}/invite/deliver", response_model=InvitationRead)
def deliver_invite(onboarding_id: UUID, request: Request, admin: AdminUser, db: DBSession) -> InvitationRead:
    record = _record_or_404(db, onboarding_id)
    if record.status not in service.EMPLOYEE_EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="This onboarding is no longer open for invitation delivery.")
    if record.invitation_expires_at is None or record.invitation_token_hash is None:
        raise HTTPException(status_code=409, detail="Generate an invitation before sending it.")
    if service.as_utc(record.invitation_expires_at) < service.utcnow():
        raise HTTPException(status_code=409, detail="The current invitation has expired. Generate a new invitation.")
    try:
        token = service.current_invitation_token(record)
    except OnboardingDataUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    base_url = str(request.base_url).rstrip("/")
    invite_url = f"{base_url}/employee-onboarding/{token}"
    delivery_status = service.deliver_invitation(
        db,
        record,
        invite_url=invite_url,
        actor=admin.email,
    )
    return InvitationRead(
        onboarding_id=record.id,
        invite_url=invite_url,
        expires_at=record.invitation_expires_at,
        delivery_status=delivery_status,
    )


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


@router.post("/{onboarding_id}/activate", response_model=PortalActivationRead)
def activate(onboarding_id: UUID, admin: AdminUser, db: DBSession) -> PortalActivationRead:
    try:
        record, employee, account, temporary_password = service.activate(
            db,
            _record_or_404(db, onboarding_id),
            admin.email,
        )
        return PortalActivationRead(
            onboarding=EmployeeOnboardingRead.model_validate(record),
            employee_id=employee.id,
            account_id=account.id,
            username=account.email,
            temporary_password=temporary_password,
            portal_role=employee.portal_role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{onboarding_id}/packet", response_model=PortalPacket)
def review_packet(onboarding_id: UUID, admin: AdminUser, db: DBSession) -> PortalPacket:
    record = _record_or_404(db, onboarding_id)
    try:
        packet = service.portal_packet(record)
    except OnboardingDataUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="Restricted onboarding data is unavailable. Administrator review is required.",
        ) from exc
    service.audit(
        db,
        record,
        "restricted_packet_viewed",
        admin.email,
        {"status": record.status},
    )
    db.commit()
    return packet


@router.get("/{onboarding_id}/orientations", response_model=list[WorkerOrientationRead])
def list_orientations(onboarding_id: UUID, user: CurrentUser, db: DBSession) -> list[WorkerOrientationRead]:
    _require_management(user)
    _record_or_404(db, onboarding_id)
    return [WorkerOrientationRead.model_validate(item) for item in service.list_orientations(db, onboarding_id)]


@router.post(
    "/{onboarding_id}/orientations",
    response_model=WorkerOrientationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_orientation(
    onboarding_id: UUID,
    payload: WorkerOrientationCreate,
    user: CurrentUser,
    db: DBSession,
) -> WorkerOrientationRead:
    _require_management(user)
    orientation = service.create_orientation(db, _record_or_404(db, onboarding_id), payload, user.email)
    return WorkerOrientationRead.model_validate(orientation)


@router.get("/{onboarding_id}/deployment-status", response_model=DeploymentStatusRead)
def deployment_status(onboarding_id: UUID, user: CurrentUser, db: DBSession) -> DeploymentStatusRead:
    _require_management(user)
    return service.deployment_status(db, _record_or_404(db, onboarding_id))


@router.get("/{onboarding_id}/orientations.csv", response_class=Response)
def export_orientations(onboarding_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    _require_management(user)
    record = _record_or_404(db, onboarding_id)
    output = io.StringIO()
    fields = [
        "worker", "worker_email", "site", "scope", "trigger", "orientation_date",
        "instructor", "supervisor", "document_version", "competency_result", "ppe_verified",
        "qualifications_verified", "worker_acknowledged_at", "topics", "supporting_document_ids",
        "created_by", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for item in service.list_orientations(db, onboarding_id):
        writer.writerow({
            "worker": f"{record.legal_first_name} {record.legal_last_name}",
            "worker_email": record.personal_email,
            "site": item.site_name or "",
            "scope": item.scope,
            "trigger": item.trigger,
            "orientation_date": item.orientation_date.isoformat(),
            "instructor": item.instructor_name,
            "supervisor": item.supervisor_name,
            "document_version": item.document_version,
            "competency_result": item.competency_result,
            "ppe_verified": item.ppe_verified,
            "qualifications_verified": item.qualifications_verified,
            "worker_acknowledged_at": item.worker_acknowledged_at.isoformat() if item.worker_acknowledged_at else "",
            "topics": json.dumps(item.topics),
            "supporting_document_ids": json.dumps(item.supporting_document_ids),
            "created_by": item.created_by,
            "created_at": item.created_at.isoformat(),
        })
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="worker-orientations-{onboarding_id}.csv"'},
    )
