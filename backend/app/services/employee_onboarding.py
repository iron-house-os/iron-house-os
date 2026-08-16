from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee_onboarding import EmployeeOnboarding, EmployeeOnboardingAudit, WorkerOrientation
from app.models.user import Employee
from app.schemas.employee_onboarding import (
    DeploymentStatusRead,
    EmployeeOnboardingCreate,
    OnboardingStatus,
    REQUIRED_ORIENTATION_TOPIC_CODES,
    WorkerOrientationCreate,
)

REQUIRED_ITEMS = [
    "personal_information",
    "emergency_contact",
    "address",
    "payroll",
    "tax_forms",
    "employment_agreements",
    "safety_orientation",
    "certifications",
    "ppe_requirements",
    "electronic_signature",
]


def utcnow() -> datetime:
    return datetime.now(UTC)


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
    if record is None or record.invitation_revoked_at is not None:
        return None
    if record.invitation_expires_at is None or record.invitation_expires_at < utcnow():
        record.status = OnboardingStatus.INVITATION_EXPIRED.value
        db.commit()
        return None
    return record


def update_progress(db: Session, record: EmployeeOnboarding, completed_items: list[str]) -> EmployeeOnboarding:
    completed = sorted(set(completed_items) & set(REQUIRED_ITEMS))
    record.completed_items = completed
    record.missing_items = [item for item in REQUIRED_ITEMS if item not in completed]
    record.completion_percent = round(len(completed) / len(REQUIRED_ITEMS) * 100)
    record.status = OnboardingStatus.IN_PROGRESS.value
    audit(db, record, "progress_saved", record.personal_email, {"completion_percent": record.completion_percent})
    db.commit()
    db.refresh(record)
    return record


def submit(db: Session, record: EmployeeOnboarding, completed_items: list[str], acknowledgement: bool) -> EmployeeOnboarding:
    update_progress(db, record, completed_items)
    if record.missing_items or not acknowledgement:
        raise ValueError("All required onboarding items and acknowledgement are required.")
    record.status = OnboardingStatus.SUBMITTED.value
    record.submitted_at = utcnow()
    record.invitation_used_at = utcnow()
    audit(db, record, "submitted", record.personal_email)
    db.commit()
    db.refresh(record)
    return record


def activate(db: Session, record: EmployeeOnboarding, actor: str) -> EmployeeOnboarding:
    if record.status != OnboardingStatus.APPROVED.value:
        raise ValueError("Onboarding must be approved before activation.")
    readiness = deployment_status(db, record)
    if readiness.status != "Ready":
        raise ValueError(f"Worker deployment is {readiness.status}: {' '.join(readiness.blockers)}")
    employee = Employee(first_name=record.legal_first_name, last_name=record.legal_last_name, email=record.personal_email, role=record.position, phone=record.mobile_phone, hire_date=record.start_date, status="active", portal_role="employee")
    db.add(employee)
    db.flush()
    record.employee_id = employee.id
    record.status = OnboardingStatus.ACTIVE.value
    record.activated_at = utcnow()
    audit(db, record, "activated", actor, {"employee_id": str(employee.id)})
    db.commit()
    db.refresh(record)
    return record
