import re
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.workflow_values import workflow_enum
from app.models.bid import Bid
from app.models.document import Document, Drawing
from app.models.project import (
    Project,
    ProjectCloseoutChecklistItem,
    ProjectStartChecklistItem,
    ProjectSupplier,
)
from app.schemas.project_closeout import (
    ProjectCloseoutChecklistItemRead,
    ProjectCloseoutChecklistRead,
    ProjectCloseoutChecklistUpdate,
)
from app.models.rfq import RFQPackage
from app.schemas.project import (
    ProjectCreate,
    ProjectDashboard,
    ProjectList,
    ProjectRead,
    ProjectStatus,
    ProjectUpdate,
)
from app.schemas.project_folder import AwardedProjectWorkspace, ProjectFolderManifest
from app.schemas.project_start import (
    ProjectStartChecklistItemRead,
    ProjectStartChecklistRead,
)
from app.services import project_folders
from app.services.auth import AuthenticatedUser

JOB_NUMBER_PREFIX = "IH"
JOB_NUMBER_WIDTH = 3
JOB_NUMBER_RETRY_LIMIT = 20
IRON_HOUSE_TIME_ZONE = ZoneInfo("America/Vancouver")
PROJECT_START_CHECKLIST: tuple[tuple[str, str, str], ...] = (
    (
        "award_contract",
        "Contract",
        "Award notice or executed contract and the client scope record are saved.",
    ),
    ("scope_review", "Contract", "Scope, exclusions, allowances, and alternates are reviewed."),
    (
        "current_documents",
        "Documents",
        "Current drawings, specifications, and addenda are confirmed.",
    ),
    (
        "contacts_authority",
        "Administration",
        "Project contacts, authority limits, and communication path are confirmed.",
    ),
    (
        "budget_cost_codes",
        "Cost control",
        "Baseline budget and project cost codes are established.",
    ),
    (
        "schedule_milestones",
        "Schedule",
        "Baseline schedule, milestones, and notice periods are established.",
    ),
    (
        "procurement_plan",
        "Procurement",
        "Subcontractor, material, equipment, and procurement plans are established.",
    ),
    (
        "permits_insurance_bonding",
        "Administration",
        "Permit, insurance, and bonding requirements are assigned.",
    ),
    (
        "safety_mobilization",
        "Safety",
        "Project-specific safety and mobilization requirements are assigned for verification.",
    ),
    (
        "quality_testing_asbuilts",
        "Quality",
        "Quality, inspection, testing, and as-built requirements are assigned.",
    ),
)
PROJECT_CLOSEOUT_CHECKLIST: tuple[tuple[str, str, str], ...] = (
    (
        "deficiencies",
        "Quality",
        "Deficiencies are closed or carried forward with an owner, due date, and documented basis.",
    ),
    (
        "testing_inspections",
        "Quality",
        "Required testing and inspection records are complete and saved to the project record.",
    ),
    (
        "permit_authority_finals",
        "Administration",
        "Permit, municipal, utility, or other authority final records are saved when applicable.",
    ),
    (
        "asbuilts_redlines",
        "Documents",
        "As-builts, redlines, and final drawing revisions are complete and indexed.",
    ),
    (
        "turnover_warranty",
        "Turnover",
        "O&M information, warranties, training, and spare-material obligations are complete or recorded as not applicable.",
    ),
    (
        "demobilization",
        "Delivery",
        "Demobilization, cleanup, environmental controls, and remaining site obligations are complete.",
    ),
    (
        "changes_commitments",
        "Cost control",
        "Final changes, purchase orders, subcontract commitments, and unresolved exposure are reconciled.",
    ),
    (
        "billing_holdback",
        "Finance",
        "Final billing package and holdback status are recorded without inferring issue, payment, or release.",
    ),
    (
        "acceptance_evidence",
        "Contract",
        "Client or consultant acceptance, substantial completion, or other contract completion evidence is saved when applicable.",
    ),
    (
        "turnover_index",
        "Documents",
        "The closeout package is indexed in the project record with remaining actions clearly assigned.",
    ),
)
PROJECT_CLOSEOUT_CODES = frozenset(code for code, _category, _label in PROJECT_CLOSEOUT_CHECKLIST)
MANAGEMENT_PROJECT_ROLES = {"admin", "operations_manager"}


def create_project(db: Session, payload: ProjectCreate) -> ProjectRead:
    values = _project_values(payload)
    if values.get("status") == ProjectStatus.completed.value:
        raise AppError(
            "Create the project through the awarded workflow and complete its closeout controls before marking it complete.",
            status_code=409,
        )
    if values.get("status") == ProjectStatus.awarded.value and not _has_job_number(
        values.get("project_number")
    ):
        return _create_awarded_project(db, values, payload.supplier_ids)

    project = Project(**values)
    db.add(project)
    db.flush()
    if project.status == ProjectStatus.awarded.value:
        _provision_awarded_workspace(db, project)
    _replace_suppliers(db, project.id, payload.supplier_ids)
    db.commit()
    return _to_schema(_load_project(db, project.id))


def list_projects(
    db: Session, status: str | None = None, include_deleted: bool = False
) -> ProjectList:
    statement = (
        select(Project)
        .options(selectinload(Project.supplier_links))
        .order_by(Project.created_at.desc())
    )
    if not include_deleted:
        statement = statement.where(Project.deleted_at.is_(None))
    if status:
        statement = statement.where(Project.status == status)
    items = [_to_schema(project) for project in db.scalars(statement).all()]
    return ProjectList(items=items, total=len(items))


def get_project(db: Session, project_id: UUID) -> ProjectRead:
    return _to_schema(_load_project(db, project_id))


def update_project(
    db: Session,
    project_id: UUID,
    payload: ProjectUpdate,
    user: AuthenticatedUser,
) -> ProjectRead:
    project = _load_project(db, project_id)
    was_awarded = project.status == ProjectStatus.awarded.value
    update_data = _project_values(payload)
    if project.project_number:
        update_data.pop("project_number", None)
    supplier_ids = payload.supplier_ids if "supplier_ids" in payload.model_fields_set else None
    resulting_status = update_data.get("status", project.status)
    resulting_number = update_data.get("project_number", project.project_number)
    status_changed = resulting_status != project.status
    if status_changed and ProjectStatus.completed.value in {project.status, resulting_status}:
        if user.role not in MANAGEMENT_PROJECT_ROLES:
            raise AppError(
                "Management access is required to complete or reopen a project.",
                status_code=403,
            )
    completing_project = status_changed and resulting_status == ProjectStatus.completed.value
    reopening_project = status_changed and project.status == ProjectStatus.completed.value
    if completing_project:
        _require_project_closeout_ready(db, project_id)
    if resulting_status == ProjectStatus.awarded.value and not _has_job_number(resulting_number):
        return _update_awarded_project(db, project_id, update_data, supplier_ids)

    for key, value in update_data.items():
        setattr(project, key, value)
    if not was_awarded and project.status == ProjectStatus.awarded.value:
        _provision_awarded_workspace(db, project)
    if completing_project or reopening_project:
        metadata = dict(project.metadata_json or {})
        if completing_project:
            metadata["closeout_completion"] = {
                "completed_by": user.email,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        else:
            metadata["closeout_reopening"] = {
                "reopened_by": user.email,
                "reopened_at": datetime.now(UTC).isoformat(),
                "reopened_to_status": resulting_status,
            }
        project.metadata_json = metadata
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
        _provision_awarded_workspace(db, project)
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
        _provision_awarded_workspace(db, project)
        if supplier_ids is not None:
            _replace_suppliers(db, project.id, supplier_ids)
        db.commit()
        return _to_schema(_load_project(db, project_id))
    raise AppError("Unable to allocate a unique job number. Try again.", status_code=409)


def _next_job_number(db: Session, award_year: int | None = None) -> str:
    year = award_year or datetime.now(IRON_HOUSE_TIME_ZONE).year
    prefix = f"{JOB_NUMBER_PREFIX}{year}"
    legacy_prefix = f"{JOB_NUMBER_PREFIX}-{year}-"
    existing = db.scalars(
        select(Project.project_number).where(
            or_(
                Project.project_number.like(f"{prefix}%"),
                Project.project_number.like(f"{legacy_prefix}%"),
            )
        )
    ).all()
    pattern = re.compile(rf"^(?:{re.escape(prefix)}|{re.escape(legacy_prefix)})(\d+)$")
    sequences = [
        int(match.group(1)) for number in existing if number and (match := pattern.match(number))
    ]
    return f"{prefix}{max(sequences, default=0) + 1:0{JOB_NUMBER_WIDTH}d}"


def _has_job_number(value: object) -> bool:
    return bool(str(value or "").strip())


def prepare_project_award(db: Session, project: Project) -> None:
    """Prepare an award inside the caller's transaction without committing it."""
    if project.status == ProjectStatus.archived.value:
        raise AppError("Archived projects cannot be awarded.", status_code=409)
    project.status = ProjectStatus.awarded.value
    if not _has_job_number(project.project_number):
        project.project_number = _next_job_number(db)
    db.flush()
    _provision_awarded_workspace(db, project)


def _provision_awarded_workspace(db: Session, project: Project) -> None:
    if not _has_job_number(project.project_number):
        raise AppError(
            "A permanent job number is required before workspace provisioning", status_code=409
        )
    if not project.workspace_root:
        manifest = project_folders.build_awarded_project_folder_manifest(
            job_number=str(project.project_number),
            project_name=project.name,
            client_owner=project.client_owner,
            municipality=project.municipality_name,
            tender_number=project.tender_number,
            tender_closing_date=project.tender_closing_date,
        )
        project.workspace_root = manifest.root_folder
        project.workspace_manifest_json = manifest.model_dump(mode="json")
        project.workspace_provisioned_at = datetime.now(UTC)
    _provision_project_start_checklist(db, project.id)
    _provision_project_closeout_checklist(db, project.id)


def _provision_project_start_checklist(db: Session, project_id: UUID) -> None:
    values = [
        {
            "project_id": project_id,
            "code": code,
            "category": category,
            "label": label,
            "sort_order": sort_order,
            "completed": False,
        }
        for sort_order, (code, category, label) in enumerate(PROJECT_START_CHECKLIST, start=1)
    ]
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "postgresql":
        statement = postgresql_insert(ProjectStartChecklistItem).values(values)
        db.execute(statement.on_conflict_do_nothing(index_elements=["project_id", "code"]))
        return
    if dialect_name == "sqlite":
        statement = sqlite_insert(ProjectStartChecklistItem).values(values)
        db.execute(statement.on_conflict_do_nothing(index_elements=["project_id", "code"]))
        return

    for value in values:
        try:
            with db.begin_nested():
                db.add(ProjectStartChecklistItem(**value))
                db.flush()
        except IntegrityError:
            continue


def _provision_project_closeout_checklist(db: Session, project_id: UUID) -> None:
    values = [
        {
            "project_id": project_id,
            "code": code,
            "category": category,
            "label": label,
            "sort_order": sort_order,
            "completed": False,
        }
        for sort_order, (code, category, label) in enumerate(
            PROJECT_CLOSEOUT_CHECKLIST,
            start=1,
        )
    ]
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "postgresql":
        statement = postgresql_insert(ProjectCloseoutChecklistItem).values(values)
        db.execute(statement.on_conflict_do_nothing(index_elements=["project_id", "code"]))
        return
    if dialect_name == "sqlite":
        statement = sqlite_insert(ProjectCloseoutChecklistItem).values(values)
        db.execute(statement.on_conflict_do_nothing(index_elements=["project_id", "code"]))
        return

    for value in values:
        try:
            with db.begin_nested():
                db.add(ProjectCloseoutChecklistItem(**value))
                db.flush()
        except IntegrityError:
            continue


def archive_project(db: Session, project_id: UUID) -> ProjectRead:
    project = _load_project(db, project_id)
    project.status = ProjectStatus.archived.value
    db.commit()
    return _to_schema(_load_project(db, project_id))


def delete_project(db: Session, project_id: UUID, confirmation_name: str) -> ProjectRead:
    project = _load_project(db, project_id)
    if confirmation_name.strip() != project.name:
        raise AppError("Enter the exact project name to confirm deletion.", status_code=409)
    project.deleted_at = datetime.now(UTC)
    db.commit()
    return _to_schema(_load_project(db, project_id, include_deleted=True))


def restore_project(db: Session, project_id: UUID) -> ProjectRead:
    project = _load_project(db, project_id, include_deleted=True)
    if project.deleted_at is None:
        raise AppError("Project is not in trash.", status_code=409)
    project.deleted_at = None
    db.commit()
    return _to_schema(_load_project(db, project_id))


def get_awarded_workspace(db: Session, project_id: UUID) -> AwardedProjectWorkspace:
    project = _load_project(db, project_id)
    if (
        not project.workspace_root
        or not project.workspace_manifest_json
        or not project.workspace_provisioned_at
        or not project.project_number
    ):
        raise AppError("Awarded project workspace not found", status_code=404)
    manifest = ProjectFolderManifest.model_validate(project.workspace_manifest_json)
    return AwardedProjectWorkspace(
        project_id=project.id,
        job_number=project.project_number,
        provisioned_at=project.workspace_provisioned_at,
        **manifest.model_dump(),
    )


def get_project_start_checklist(db: Session, project_id: UUID) -> ProjectStartChecklistRead:
    _load_project(db, project_id)
    items = db.scalars(
        select(ProjectStartChecklistItem)
        .where(ProjectStartChecklistItem.project_id == project_id)
        .order_by(ProjectStartChecklistItem.sort_order)
    ).all()
    if not items:
        raise AppError("Awarded project start checklist not found", status_code=404)
    return _project_start_checklist_schema(project_id, items)


def update_project_start_checklist_item(
    db: Session,
    project_id: UUID,
    code: str,
    completed: bool,
    actor: str,
) -> ProjectStartChecklistRead:
    _load_project(db, project_id)
    item = db.scalar(
        select(ProjectStartChecklistItem).where(
            ProjectStartChecklistItem.project_id == project_id,
            ProjectStartChecklistItem.code == code,
        )
    )
    if item is None:
        raise AppError("Project start checklist item not found", status_code=404)
    item.completed = completed
    item.changed_by = actor
    item.changed_at = datetime.now(UTC)
    db.commit()
    return get_project_start_checklist(db, project_id)


def _project_start_checklist_schema(
    project_id: UUID,
    items: list[ProjectStartChecklistItem],
) -> ProjectStartChecklistRead:
    completed_count = sum(1 for item in items if item.completed)
    return ProjectStartChecklistRead(
        project_id=project_id,
        status="ready" if completed_count == len(items) else "not_ready",
        completed_count=completed_count,
        total_count=len(items),
        items=[
            ProjectStartChecklistItemRead(
                code=item.code,
                category=item.category,
                label=item.label,
                sort_order=item.sort_order,
                completed=item.completed,
                changed_by=item.changed_by,
                changed_at=item.changed_at,
            )
            for item in items
        ],
    )


def initialize_project_closeout_checklist(
    db: Session,
    project_id: UUID,
    user: AuthenticatedUser,
) -> ProjectCloseoutChecklistRead:
    if user.role not in MANAGEMENT_PROJECT_ROLES:
        raise AppError(
            "Management access is required to initialize project closeout controls.",
            status_code=403,
        )
    project = _load_project(db, project_id)
    if (
        project.status
        not in {
            ProjectStatus.awarded.value,
            ProjectStatus.construction.value,
            ProjectStatus.completed.value,
        }
        or not project.project_number
    ):
        raise AppError(
            "Closeout controls are available only for awarded jobs with a permanent job number.",
            status_code=409,
        )
    _provision_project_closeout_checklist(db, project_id)
    db.commit()
    return get_project_closeout_checklist(db, project_id)


def get_project_closeout_checklist(
    db: Session,
    project_id: UUID,
) -> ProjectCloseoutChecklistRead:
    _load_project(db, project_id)
    items = list(
        db.scalars(
            select(ProjectCloseoutChecklistItem)
            .where(ProjectCloseoutChecklistItem.project_id == project_id)
            .order_by(ProjectCloseoutChecklistItem.sort_order)
        ).all()
    )
    if not items:
        raise AppError("Project closeout checklist not found", status_code=404)
    return _project_closeout_checklist_schema(project_id, items)


def update_project_closeout_checklist_item(
    db: Session,
    project_id: UUID,
    code: str,
    payload: ProjectCloseoutChecklistUpdate,
    user: AuthenticatedUser,
) -> ProjectCloseoutChecklistRead:
    if user.role not in MANAGEMENT_PROJECT_ROLES:
        raise AppError(
            "Management access is required to update project closeout controls.",
            status_code=403,
        )
    project = _load_project(db, project_id)
    if project.status == ProjectStatus.completed.value and not payload.completed:
        raise AppError(
            "Reopen the project before reopening a completed closeout control.",
            status_code=409,
        )
    item = db.scalar(
        select(ProjectCloseoutChecklistItem).where(
            ProjectCloseoutChecklistItem.project_id == project_id,
            ProjectCloseoutChecklistItem.code == code,
        )
    )
    if item is None:
        raise AppError("Project closeout checklist item not found", status_code=404)
    item.completed = payload.completed
    item.evidence = payload.evidence if payload.completed else None
    item.changed_by = user.email
    item.changed_at = datetime.now(UTC)
    db.commit()
    return get_project_closeout_checklist(db, project_id)


def _project_closeout_checklist_schema(
    project_id: UUID,
    items: list[ProjectCloseoutChecklistItem],
) -> ProjectCloseoutChecklistRead:
    completed_count = sum(1 for item in items if item.completed)
    next_item = next((item for item in items if not item.completed), None)
    item_schemas = [
        ProjectCloseoutChecklistItemRead(
            code=item.code,
            category=item.category,
            label=item.label,
            sort_order=item.sort_order,
            completed=item.completed,
            evidence=item.evidence,
            changed_by=item.changed_by,
            changed_at=item.changed_at,
        )
        for item in items
    ]
    total_count = len(items)
    has_exact_controls = {item.code for item in items} == PROJECT_CLOSEOUT_CODES
    return ProjectCloseoutChecklistRead(
        project_id=project_id,
        status=("ready" if has_exact_controls and completed_count == total_count else "not_ready"),
        completed_count=completed_count,
        total_count=total_count,
        next_incomplete_control=(
            next((item for item in item_schemas if item.code == next_item.code), None) if next_item else None
        ),
        items=item_schemas,
    )


def _require_project_closeout_ready(db: Session, project_id: UUID) -> None:
    items = list(
        db.scalars(
            select(ProjectCloseoutChecklistItem).where(ProjectCloseoutChecklistItem.project_id == project_id)
        ).all()
    )
    if {item.code for item in items} != PROJECT_CLOSEOUT_CODES or any(
        not item.completed or not str(item.evidence or "").strip() for item in items
    ):
        raise AppError(
            "Complete every project closeout control with evidence before marking the project complete.",
            status_code=409,
        )


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
            select(func.count())
            .select_from(Document)
            .where(
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


def _load_project(db: Session, project_id: UUID, include_deleted: bool = False) -> Project:
    statement = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.supplier_links))
    )
    if not include_deleted:
        statement = statement.where(Project.deleted_at.is_(None))
    project = db.scalar(statement)
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
        contract_value=(
            float(project.contract_value) if project.contract_value is not None else None
        ),
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
        workspace_root=project.workspace_root,
        workspace_provisioned_at=project.workspace_provisioned_at,
        deleted_at=project.deleted_at,
        supplier_ids=[link.supplier_id for link in project.supplier_links],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
