from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
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


def create_project(db: Session, payload: ProjectCreate) -> ProjectRead:
    project = Project(**_project_values(payload))
    db.add(project)
    db.flush()
    _replace_suppliers(db, project.id, payload.supplier_ids)
    db.commit()
    return _to_schema(_load_project(db, project.id))


def list_projects(db: Session, status: str | None = None) -> ProjectList:
    statement = (
        select(Project)
        .options(selectinload(Project.supplier_links))
        .order_by(Project.created_at.desc())
    )
    if status:
        statement = statement.where(Project.status == status)
    items = [_to_schema(project) for project in db.scalars(statement).all()]
    return ProjectList(items=items, total=len(items))


def get_project(db: Session, project_id: UUID) -> ProjectRead:
    return _to_schema(_load_project(db, project_id))


def update_project(db: Session, project_id: UUID, payload: ProjectUpdate) -> ProjectRead:
    project = _load_project(db, project_id)
    update_data = _project_values(payload)
    supplier_ids = (
        payload.supplier_ids if "supplier_ids" in payload.model_fields_set else None
    )
    for key, value in update_data.items():
        setattr(project, key, value)
    if supplier_ids is not None:
        _replace_suppliers(db, project.id, supplier_ids)
    db.commit()
    return _to_schema(_load_project(db, project_id))


def archive_project(db: Session, project_id: UUID) -> ProjectRead:
    project = _load_project(db, project_id)
    project.status = ProjectStatus.archived.value
    db.commit()
    return _to_schema(_load_project(db, project_id))


def get_project_dashboard(db: Session, project_id: UUID) -> ProjectDashboard:
    project = _load_project(db, project_id)
    rfq_count = (
        db.scalar(
            select(func.count()).select_from(RFQPackage).where(RFQPackage.project_id == project_id)
        )
        or 0
    )
    supplier_count = (
        db.scalar(
            select(func.count())
            .select_from(ProjectSupplier)
            .where(ProjectSupplier.project_id == project_id)
        )
        or 0
    )
    document_count = (
        db.scalar(
            select(func.count()).select_from(Document).where(Document.project_id == project_id)
        )
        or 0
    )
    drawing_count = (
        db.scalar(
            select(func.count()).select_from(Document).where(
                Document.project_id == project_id,
                Document.category == "drawing",
            )
        )
        or 0
    )
    drawing_count += (
        db.scalar(select(func.count()).select_from(Drawing).where(Drawing.project_id == project_id))
        or 0
    )
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
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.supplier_links))
    )
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
    db.add_all(
        ProjectSupplier(project_id=project_id, supplier_id=supplier_id)
        for supplier_id in supplier_ids
    )


def _bid_status(db: Session, project_id: UUID) -> str:
    bid = db.scalar(
        select(Bid).where(Bid.project_id == project_id).order_by(Bid.created_at.desc())
    )
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
        contract_value=(
            float(project.contract_value) if project.contract_value is not None else None
        ),
        status=ProjectStatus(project.status),
        notes=project.notes,
        metadata=project.metadata_json or {},
        supplier_ids=[link.supplier_id for link in project.supplier_links],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
