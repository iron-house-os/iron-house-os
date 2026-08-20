from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee_onboarding import EmployeeOnboarding, EmployeeOnboardingAudit, WorkerOrientation
from app.models.user import Employee, UserAccount
from app.schemas.employee_onboarding import (
    DeploymentStatusRead,
    EmployeeOnboardingCreate,
    EmploymentPosition,
    OnboardingStatus,
    PortalOnboardingRead,
    PortalPacket,
    REQUIRED_ORIENTATION_TOPIC_CODES,
    WorkerOrientationCreate,
)
from app.services.auth import hash_password
from app.services.onboarding_data import decrypt_packet, encrypt_packet

EMPLOYEE_PACKET_SECTIONS = [
    "personal_information",
    "emergency_contact",
    "address",
    "payroll",
    "tax_forms",
    "employment_agreements",
    "certifications",
    "ppe_requirements",
]
REQUIRED_ITEMS = [
    *EMPLOYEE_PACKET_SECTIONS,
    "electronic_signature",
]
INVITABLE_STATUSES = {
    OnboardingStatus.DRAFT.value,
    OnboardingStatus.INVITATION_SENT.value,
    OnboardingStatus.INVITATION_OPENED.value,
    OnboardingStatus.IN_PROGRESS.value,
    OnboardingStatus.CORRECTIONS_REQUIRED.value,
    OnboardingStatus.INVITATION_EXPIRED.value,
}
EMPLOYEE_EDITABLE_STATUSES = {
    OnboardingStatus.INVITATION_SENT.value,
    OnboardingStatus.INVITATION_OPENED.value,
    OnboardingStatus.IN_PROGRESS.value,
    OnboardingStatus.CORRECTIONS_REQUIRED.value,
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def audit(db: Session, onboarding: EmployeeOnboarding, action: str, actor: str, metadata: dict | None = None) -> None:
    db.add(EmployeeOnboardingAudit(onboarding_id=onboarding.id, action=action, actor=actor, metadata_json=metadata or {}, created_at=utcnow()))


def create(db: Session, payload: EmployeeOnboardingCreate, actor: str) -> EmployeeOnboarding:
    record = EmployeeOnboarding(**payload.model_dump(mode="json"), status=OnboardingStatus.DRAFT.value, missing_items=REQUIRED_ITEMS.copy())
    db.add(record)
    db.flush()
    audit(db, record, "created", actor)
    db.commit()
    db.refresh(record)
    return record


def list_records(db: Session) -> list[EmployeeOnboarding]:
    return list(db.scalars(select(EmployeeOnboarding).order_by(EmployeeOnboarding.created_at.desc())))


def get(db: Session, onboarding_id: UUID) -> EmployeeOnboarding | None:
    return db.get(EmployeeOnboarding, onboarding_id)


def list_orientations(db: Session, onboarding_id: UUID) -> list[WorkerOrientation]:
    statement = (
        select(WorkerOrientation)
        .where(WorkerOrientation.onboarding_id == onboarding_id)
        .order_by(WorkerOrientation.orientation_date.desc(), WorkerOrientation.created_at.desc())
    )
    return list(db.scalars(statement))


def create_orientation(
    db: Session,
    record: EmployeeOnboarding,
    payload: WorkerOrientationCreate,
    actor: str,
) -> WorkerOrientation:
    orientation = WorkerOrientation(
        onboarding_id=record.id,
        created_by=actor,
        **payload.model_dump(mode="json"),
    )
    db.add(orientation)
    db.flush()
    audit(
        db,
        record,
        "worker_orientation_recorded",
        actor,
        {"orientation_id": str(orientation.id), "scope": orientation.scope, "trigger": orientation.trigger},
    )
    db.commit()
    db.refresh(orientation)
    return orientation


def _orientation_evidence_complete(orientation: WorkerOrientation) -> bool:
    topics = orientation.topics or []
    topic_codes = {topic.get("code") for topic in topics}
    topics_complete = len(topics) == len(topic_codes) and topic_codes == set(REQUIRED_ORIENTATION_TOPIC_CODES)
    evidence_complete = all(
        bool((topic.get("evidence") or "").strip())
        if topic.get("applicability") == "applicable"
        else bool((topic.get("not_applicable_basis") or "").strip())
        for topic in topics
    )
    return bool(
        topics_complete
        and evidence_complete
        and orientation.worker_acknowledged
        and orientation.worker_acknowledged_at
        and orientation.ppe_verified
        and orientation.qualifications_verified
    )


def deployment_status(db: Session, record: EmployeeOnboarding) -> DeploymentStatusRead:
    orientations = list_orientations(db, record.id)
    company = next((item for item in orientations if item.scope == "company"), None)
    site = next((item for item in orientations if item.scope == "site"), None)
    blockers: list[str] = []

    if company is None:
        blockers.append("Company orientation has not been recorded.")
    elif not _orientation_evidence_complete(company):
        blockers.append("Company orientation evidence is incomplete.")
    elif company.competency_result != "passed":
        blockers.append("Company orientation competency has not been assessed as passed.")

    if blockers:
        return DeploymentStatusRead(
            status="Blocked",
            blockers=blockers,
            latest_company_orientation_id=company.id if company else None,
            latest_site_orientation_id=site.id if site else None,
        )

    if record.category == "field_staff":
        if site is None:
            blockers.append("Site orientation has not been recorded.")
        elif not _orientation_evidence_complete(site):
            blockers.append("Site orientation evidence is incomplete.")
        elif site.competency_result != "passed":
            blockers.append("Site orientation competency has not been assessed as passed.")
        if blockers:
            return DeploymentStatusRead(
                status="Supervised work only",
                blockers=blockers,
                latest_company_orientation_id=company.id,
                latest_site_orientation_id=site.id if site else None,
            )

    return DeploymentStatusRead(
        status="Ready",
        blockers=[],
        latest_company_orientation_id=company.id,
        latest_site_orientation_id=site.id if site else None,
    )


def issue_invitation(db: Session, record: EmployeeOnboarding, actor: str, ttl_hours: int = 72) -> tuple[str, datetime]:
    if record.status not in INVITABLE_STATUSES:
        raise ValueError("Onboarding is not eligible for a new invitation.")
    token = secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(hours=ttl_hours)
    record.invitation_token_hash = hashlib.sha256(token.encode()).hexdigest()
    record.invitation_expires_at = expires_at
    record.invitation_revoked_at = None
    record.invitation_used_at = None
    record.invited_at = utcnow()
    record.status = OnboardingStatus.INVITATION_SENT.value
    audit(db, record, "invitation_sent", actor, {"expires_at": expires_at.isoformat()})
    db.commit()
    return token, expires_at


def resolve_token(db: Session, token: str) -> EmployeeOnboarding | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    record = db.scalar(select(EmployeeOnboarding).where(EmployeeOnboarding.invitation_token_hash == token_hash))
    if (
        record is None
        or record.invitation_revoked_at is not None
        or record.status
        in {
            OnboardingStatus.APPROVED.value,
            OnboardingStatus.ACTIVE.value,
            OnboardingStatus.CANCELLED.value,
        }
    ):
        return None
    if record.invitation_expires_at is None or as_utc(record.invitation_expires_at) < utcnow():
        record.status = OnboardingStatus.INVITATION_EXPIRED.value
        db.commit()
        return None
    return record


def portal_packet(record: EmployeeOnboarding) -> PortalPacket:
    return decrypt_packet(record.encrypted_portal_data)


def portal_read(record: EmployeeOnboarding) -> PortalOnboardingRead:
    return PortalOnboardingRead(
        onboarding=record,
        packet=portal_packet(record),
    )


def _completed_packet_sections(packet: PortalPacket) -> list[str]:
    return [
        section
        for section in EMPLOYEE_PACKET_SECTIONS
        if getattr(packet, section) is not None
    ]


def update_progress(db: Session, record: EmployeeOnboarding, packet: PortalPacket) -> EmployeeOnboarding:
    if record.status not in EMPLOYEE_EDITABLE_STATUSES:
        raise ValueError("Onboarding is not open for employee changes.")
    packet = packet.model_copy(update={"signature_name": None, "signed_at": None})
    completed = _completed_packet_sections(packet)
    record.encrypted_portal_data = encrypt_packet(packet)
    if packet.personal_information is not None:
        record.preferred_name = packet.personal_information.preferred_name
        record.mobile_phone = packet.personal_information.mobile_phone
    record.completed_items = completed
    record.missing_items = [item for item in REQUIRED_ITEMS if item not in completed]
    record.completion_percent = round(len(completed) / len(REQUIRED_ITEMS) * 100)
    record.status = OnboardingStatus.IN_PROGRESS.value
    audit(
        db,
        record,
        "progress_saved",
        record.personal_email,
        {
            "completion_percent": record.completion_percent,
            "completed_sections": completed,
        },
    )
    db.commit()
    db.refresh(record)
    return record


def submit(
    db: Session,
    record: EmployeeOnboarding,
    packet: PortalPacket,
    acknowledgement: bool,
    signature_name: str,
) -> EmployeeOnboarding:
    if record.status not in EMPLOYEE_EDITABLE_STATUSES:
        raise ValueError("Onboarding is not open for submission.")
    completed = _completed_packet_sections(packet)
    missing_sections = [
        section for section in EMPLOYEE_PACKET_SECTIONS if section not in completed
    ]
    if missing_sections or not acknowledgement or not signature_name.strip():
        raise ValueError("All required onboarding forms, acknowledgement, and signature are required.")
    signed_packet = packet.model_copy(
        update={
            "signature_name": signature_name.strip(),
            "signed_at": utcnow(),
        }
    )
    record.encrypted_portal_data = encrypt_packet(signed_packet)
    if packet.personal_information is not None:
        record.preferred_name = packet.personal_information.preferred_name
        record.mobile_phone = packet.personal_information.mobile_phone
    record.completed_items = REQUIRED_ITEMS.copy()
    record.missing_items = []
    record.completion_percent = 100
    record.status = OnboardingStatus.SUBMITTED.value
    record.submitted_at = utcnow()
    record.invitation_used_at = utcnow()
    audit(
        db,
        record,
        "submitted",
        record.personal_email,
        {"completed_sections": REQUIRED_ITEMS.copy()},
    )
    db.commit()
    db.refresh(record)
    return record


def portal_role_for_position(position: str) -> str:
    if position == EmploymentPosition.EQUIPMENT_OPERATOR.value:
        return "operator"
    if position in {
        EmploymentPosition.FOREMAN.value,
        EmploymentPosition.SUPERINTENDENT.value,
    }:
        return "foreman"
    return "employee"


def activate(
    db: Session,
    record: EmployeeOnboarding,
    actor: str,
) -> tuple[EmployeeOnboarding, Employee, UserAccount, str]:
    if record.status != OnboardingStatus.APPROVED.value:
        raise ValueError("Onboarding must be approved before activation.")
    if record.employee_id is not None:
        raise ValueError("Onboarding has already been activated.")
    readiness = deployment_status(db, record)
    if readiness.status != "Ready":
        raise ValueError(f"Worker deployment is {readiness.status}: {' '.join(readiness.blockers)}")

    username = record.personal_email.strip().lower()
    existing_employee = db.scalar(
        select(Employee.id).where(func.lower(Employee.email) == username)
    )
    if existing_employee is not None:
        raise ValueError("An employee with that email already exists.")
    existing_account = db.scalar(
        select(UserAccount.id).where(func.lower(UserAccount.email) == username)
    )
    if existing_account is not None:
        raise ValueError("A portal account with that email already exists and requires administrator review.")

    portal_role = portal_role_for_position(record.position)
    temporary_password = secrets.token_urlsafe(18)
    employee = Employee(
        first_name=record.legal_first_name,
        last_name=record.legal_last_name,
        email=username,
        role=record.position,
        phone=record.mobile_phone,
        hire_date=record.start_date,
        status="active",
        portal_role=portal_role,
    )
    account = UserAccount(
        email=username,
        display_name=f"{record.preferred_name or record.legal_first_name} {record.legal_last_name}",
        role="viewer",
        password_hash=hash_password(temporary_password),
        is_active=True,
        session_version=1,
        password_reset_required=True,
    )
    db.add_all([employee, account])
    db.flush()
    record.employee_id = employee.id
    record.status = OnboardingStatus.ACTIVE.value
    record.activated_at = utcnow()
    audit(
        db,
        record,
        "activated",
        actor,
        {
            "employee_id": str(employee.id),
            "account_id": str(account.id),
            "portal_role": portal_role,
        },
    )
    db.commit()
    db.refresh(record)
    db.refresh(employee)
    db.refresh(account)
    return record, employee, account, temporary_password
