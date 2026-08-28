from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.bid import Bid
from app.models.document import Document
from app.models.field_operations import FieldRecord
from app.models.finance import FinancialEntry
from app.models.project import Project, ProjectStartChecklistItem
from app.schemas.project import ProjectStatus
from app.schemas.project_launch import ProjectLaunchDashboard, ProjectLaunchNextControl
from app.services import project_safety_launch

SAFETY_RECORD_TYPES = (
    "safety_permit",
    "emergency_action_card",
    "daily_hazard_assessment",
    "toolbox_talk",
    "corrective_action",
)


def get_project_launch_dashboard(db: Session, project_id: UUID) -> ProjectLaunchDashboard:
    project = db.get(Project, project_id)
    if project is None:
        raise AppError("Project not found.", status_code=404)
    if project.status != ProjectStatus.awarded.value or not project.project_number:
        raise AppError("The launch dashboard is available only for awarded jobs.", status_code=409)

    checklist = list(
        db.scalars(
            select(ProjectStartChecklistItem)
            .where(ProjectStartChecklistItem.project_id == project_id)
            .order_by(ProjectStartChecklistItem.sort_order)
        ).all()
    )
    completed_count = sum(item.completed for item in checklist)
    next_item = next((item for item in checklist if not item.completed), None)

    bids = list(db.scalars(select(Bid).where(Bid.project_id == project_id)).all())
    priced_estimate_available = any(
        bid.total_amount is not None or bool((bid.bid_json or {}).get("summary"))
        for bid in bids
    )

    budget_rows = list(
        db.scalars(
            select(FinancialEntry).where(
                FinancialEntry.project_id == project_id,
                FinancialEntry.entry_type == "budget",
                FinancialEntry.status != "void",
            )
        ).all()
    )
    baseline_budget_total = round(sum(float(row.amount) for row in budget_rows), 2)

    po_rows = list(
        db.scalars(
            select(FieldRecord).where(
                FieldRecord.project_id == project_id,
                FieldRecord.record_type == "purchase_order_request",
            )
        ).all()
    )
    safety_counts = {record_type: 0 for record_type in SAFETY_RECORD_TYPES}
    safety_rows = db.execute(
        select(FieldRecord.record_type, func.count(FieldRecord.id))
        .where(
            FieldRecord.project_id == project_id,
            FieldRecord.record_type.in_(SAFETY_RECORD_TYPES),
        )
        .group_by(FieldRecord.record_type)
    ).all()
    for record_type, count in safety_rows:
        safety_counts[str(record_type)] = int(count)

    document_count = int(
        db.scalar(select(func.count(Document.id)).where(Document.project_id == project_id)) or 0
    )
    metadata = project.metadata_json or {}
    safety_launch = project_safety_launch.read(project)
    award_baseline = metadata.get("award_pricing_baseline") or {}
    procurement_plan = metadata.get("procurement_plan") or {}
    award_lines = award_baseline.get("lines") or []
    cost_budget_lines = award_baseline.get("cost_budget_lines") or []
    requirements = procurement_plan.get("requirements") or []
    total_count = len(checklist)
    return ProjectLaunchDashboard(
        project_id=project.id,
        job_number=project.project_number,
        mobilization_status=(
            "ready" if total_count > 0 and completed_count == total_count else "not_ready"
        ),
        checklist_completed_count=completed_count,
        checklist_total_count=total_count,
        next_incomplete_control=(
            ProjectLaunchNextControl(
                code=next_item.code,
                category=next_item.category,
                label=next_item.label,
            )
            if next_item
            else None
        ),
        estimate_workspace_count=len(bids),
        priced_estimate_available=priced_estimate_available,
        baseline_budget_total=baseline_budget_total,
        budget_entry_count=len(budget_rows),
        po_request_count=len(po_rows),
        pending_po_request_count=sum(row.status == "pending_approval" for row in po_rows),
        safety_record_counts=safety_counts,
        safety_release_status=(
            safety_launch.release_status if safety_launch else "not_initialized"
        ),
        safety_requirement_count=(
            len(safety_launch.record_requirements) if safety_launch else 0
        ),
        safety_folder_status=(
            safety_launch.folder_status if safety_launch else "not_initialized"
        ),
        portal_access_status=(
            safety_launch.portal_access.status if safety_launch else "not_initialized"
        ),
        portal_assignment_count=(
            len(safety_launch.portal_access.assignments) if safety_launch else 0
        ),
        document_count=document_count,
        award_baseline_source=award_baseline.get("source_quote_number"),
        award_pricing_subtotal=round(float(award_baseline.get("pricing_subtotal") or 0), 2),
        award_cost_budget_status=str(award_baseline.get("cost_budget_status") or "not_started"),
        uncoded_award_line_count=sum(
            not line.get("cost_code") for line in (cost_budget_lines or award_lines)
        ),
        procurement_requirement_count=len(requirements),
        procurement_plan_status=str(procurement_plan.get("status") or "not_started"),
    )
