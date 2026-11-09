from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ProjectLaunchNextControl(BaseModel):
    code: str
    category: str
    label: str


class ProjectLaunchDashboard(BaseModel):
    project_id: UUID
    job_number: str
    mobilization_status: Literal["ready", "not_ready"]
    checklist_completed_count: int
    checklist_total_count: int
    next_incomplete_control: ProjectLaunchNextControl | None
    estimate_workspace_count: int
    priced_estimate_available: bool
    baseline_budget_total: float
    budget_entry_count: int
    po_request_count: int
    pending_po_request_count: int
    safety_record_counts: dict[str, int]
    safety_release_status: str
    safety_requirement_count: int
    safety_folder_status: str
    portal_access_status: str
    portal_assignment_count: int
    production_posting_status: Literal["blocked", "ready"]
    production_blockers: list[str]
    daily_sheet_count: int
    production_post_count: int
    latest_daily_sheet_status: str
    field_production_folder_status: str
    document_count: int
    award_baseline_source: str | None
    award_pricing_subtotal: float
    award_cost_budget_status: str
    uncoded_award_line_count: int
    procurement_requirement_count: int
    procurement_plan_status: str
