import re
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.workflow_values import workflow_enum
from app.models.bid import Bid
from app.models.document import Document, Drawing
from app.models.project import Project, ProjectSupplier
from app.models.rfq import RFQPackage
from app.schemas.project import (
    ProjectCreate,
    ProjectDashboard,
    ProjectList,
    ProjectRead,
    ProjectStatus,
    ProjectUpdate,
)

JOB_NUMBER_PREFIX = "IH"
JOB_NUMBER_WIDTH = 3
JOB_NUMBER_RETRY_LIMIT = 20
IRON_HOUSE_TIME_ZONE = ZoneInfo("America/Vancouver")


def create_project(db: Session, payload: ProjectCreate) -> ProjectRead:
    values = _project_values(payload)
    if values.get("status") == ProjectStatus.awarded.value and not _has_job_number(values.get("project_number")):
        return _create_awarded_project(db, values, payload.supplier_ids)

    project = Project(**values)
    db.add(project)
    db.flush()
    _replace_suppliers(db, project.id, payload.supplier_ids)
    db.commit()
    return _to_schema(_load_project(db, project.id))


def list_projects(db: Session, status: str | None = None) -> ProjectList:
    statement = select(Project).options(selectinload(Project.supplier_links)).order_by(Project.created_at.desc())
    if status:
        statement = statement.where(Project.status == status)
    items = [_to_schema(project) for project in db.scalars(statement).all()]
    return ProjectList(items=items, total=len(items))


def get_project(db: Session, project_id: UUID) -> ProjectRead:
    return _to_schema(_load_project(db, project_id))


def update_project(db: Session, project_id: UUID, payload: ProjectUpdate) -> ProjectRead:
    project = _load_project(db, project_id)
    update_data = _project_values(payload)
    if project.project_number:
        update_data.pop("project_number", None)
    supplier_ids = payload.supplier_ids if "supplier_ids" in payload.model_fields_set else None
    resulting_status = update_data.get("status", project.status)
    resulting_number = update_data.get("project_number", project.project_number)
    if resulting_status == ProjectStatus.awarded.value and not _has_job_number(resulting_number):
        return _update_awarded_project(db, project_id, update_data, supplier_ids)

    for key, value in update_data.items():
        setattr(project, key, value)
    if supplier_ids is not None:
        _replace_suppliers(db, project.id, supplier_ids)
    db.commit()
    return _to_schema(_load_project(db, project_id))


def _create_awarded_project(db: Session, values: dict, supplier_ids: list[UUID]) -> ProjectRead:
    for _ in range(JOB_NUMBER_RETRY_LIMIT):
        project = Project(**{**values, "project_number": _next_job_number(db)})
        db.add(project)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            continue
        _replace_suppliers(db, project.id, supplier_ids)
        db.commit()
        return _to_schema(_load_project(db, project.id))
    raise AppError("Unable to allocate a unique job number. Try again.", status_code=409)


def _update_awarded_project(
    db: Session,
    project_id: UUID,
    update_data: dict,
    supplier_ids: list[UUID] | None,
) -> ProjectRead:
    for _ in range(JOB_NUMBER_RETRY_LIMIT):
        project = _load_project(db, project_id)
        for key, value in update_data.items():
            if key != "project_number" or not project.project_number:
                setattr(project, key, value)
        if not _has_job_number(project.project_number):
            project.project_number = _next_job_number(db)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            continue
        if supplier_ids is not None:
            _replace_suppliers(db, project.id, supplier_ids)
        db.commit()
        return _to_schema(_load_project(db, project_id))
    raise AppError("Unable to allocate a unique job number. Try again.", status_code=409)


def _next_job_number(db: Session, award_year: int | None = None) -> str:
    year = award_year or datetime.now(IRON_HOUSE_TIME_ZONE).year
    prefix = f"{JOB_NUMBER_PREFIX}-{year}-"
    existing = db.scalars(select(Project.project_number).where(Project.project_number.like(f"{prefix}%"))).all()
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    sequences = [int(match.group(1)) for number in existing if number and (match := pattern.match(number))]
    return f"{prefix}{max(sequences, default=0) + 1:0{JOB_NUMBER_WIDTH}d}"


def _has_job_number(value: object) -> bool:
    return bool(str(value or "").strip())


def archive_project(db: Session, project_id: UUID) -> ProjectRead:
    project = _load_project(db, project_id)
    project.status = ProjectStatus.archived.value
    db.commit()
    return _to_schema(_load_project(db, project_id))


def get_project_dashboard(db: Session, project_id: UUID) -> ProjectDashboard:
    project = _load_project(db, project_id)
    rfq_count = db.scalar(select(func.count()).select_from(RFQPackage).where(RFQPackage.project_id == project_id)) or 0
    supplier_count = (
        db.scalar(select(func.count()).select_from(ProjectSupplier).where(ProjectSupplier.project_id == project_id))
        or 0
    )
    document_count = db.scalar(select(func.count()).select_from(Document).where(Document.project_id == project_id)) or 0
    drawing_count = (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(
                Document.project_id == project_id,
                Document.category == "drawing",
            )
        )
        or 0
    )
    drawing_count += db.scalar(select(func.count()).select_from(Drawing).where(Drawing.project_id == project_id)) or 0
    bid_status = _bid_status(db, project_id)
    readiness_percentage = _readiness_percentage(
        rfq_count=rfq_count,
        supplier_count=supplier_count,
        document_count=document_count,
        drawing_count=drawing_count,
        bid_status=bid_status,
    )
    return ProjectDashboard(
        project_id=project.id,
        rfq_count=rfq_count,
        supplier_count=supplier_count,
        document_count=document_count,
        drawing_count=drawing_count,
        bid_status=bid_status,
        readiness_percentage=readiness_percentage,
    )


def _load_project(db: Session, project_id: UUID) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id).options(selectinload(Project.supplier_links)))
    if project is None:
        raise AppError("Project not found", status_code=404)
    return project


def _project_values(payload: ProjectCreate | ProjectUpdate) -> dict:
    data = payload.model_dump(exclude={"metadata", "supplier_ids"}, exclude_unset=True)
    if "municipality" in data:
        data["municipality_name"] = data.pop("municipality")
    status = data.get("status")
    if status is not None:
        data["status"] = status.value
    if "metadata" in payload.model_fields_set or isinstance(payload, ProjectCreate):
        data["metadata_json"] = payload.metadata or {}
    if "description" in data:
        data.pop("description")
    return data


def _replace_suppliers(db: Session, project_id: UUID, supplier_ids: list[UUID]) -> None:
    db.execute(delete(ProjectSupplier).where(ProjectSupplier.project_id == project_id))
    db.add_all(ProjectSupplier(project_id=project_id, supplier_id=supplier_id) for supplier_id in supplier_ids)


def _bid_status(db: Session, project_id: UUID) -> str:
    bid = db.scalar(select(Bid).where(Bid.project_id == project_id).order_by(Bid.created_at.desc()))
    return bid.status if bid else "not_started"


def _readiness_percentage(
    rfq_count: int,
    supplier_count: int,
    document_count: int,
    drawing_count: int,
    bid_status: str,
) -> int:
    checks = [
        rfq_count > 0,
        supplier_count > 0,
        document_count > 0,
        drawing_count > 0,
        bid_status != "not_started",
    ]
    return round((sum(1 for check in checks if check) / len(checks)) * 100)


def _to_schema(project: Project) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        name=project.name,
        client_owner=project.client_owner,
        municipality=project.municipality_name,
        project_number=project.project_number,
        tender_number=project.tender_number,
        tender_source=project.tender_source,
        tender_closing_date=project.tender_closing_date,
        bid_due_date=project.bid_due_date,
        estimated_construction_start=project.estimated_construction_start,
        estimated_construction_finish=project.estimated_construction_finish,
        project_address=project.project_address,
        latitude=project.latitude,
        longitude=project.longitude,
        contract_value=(float(project.contract_value) if project.contract_value is not None else None),
        status=workflow_enum(
            ProjectStatus,
            project.status,
            fallback=ProjectStatus.opportunity,
            aliases={
                "planning": "opportunity",
                "draft": "opportunity",
                "open": "tendering",
                "active": "construction",
                "in_progress": "construction",
                "closed": "completed",
            },
        ),
        notes=project.notes,
        metadata=project.metadata_json or {},
        supplier_ids=[link.supplier_id for link in project.supplier_links],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
