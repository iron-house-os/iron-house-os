"""Verify Bennett field-production posting remains fail-closed in staging."""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.field_operations import FieldRecord, TimeEntry
from app.models.project import ProjectStartChecklistItem
from app.services.drive_tender_import import ImportValidationError
from app.services.project_launch import SAFETY_RECORD_TYPES
from app.tools.bennett_cost_budget_staging_pilot import (
    EXPECTED_BUDGET,
    JOB_NUMBER,
    PROJECT_ID,
    QUOTE_ID,
    STAGING_BASE_URL,
    WORKSPACE_ID,
    Api,
    ApiClient,
    _money,
    _verify_exact_source,
    _verify_financial_summary,
)
from app.tools.bennett_estimate_quote_staging_pilot import _require_value
from app.tools.bennett_procurement_staging_pilot import _verify_procurement_plan
from app.tools.bennett_safety_launch_staging_pilot import (
    EXPECTED_REQUIREMENTS,
    _verify_safety_launch,
)


APPROVAL_BOUNDARY = "staging_production_gate_only_no_field_records"
EXPECTED_BLOCKERS = [
    "safety_release",
    "safety_records",
    "portal_access",
    "mobilization",
]
PRODUCTION_FOLDER_SUFFIX = "/13_Award_Handoff/Field_Production"
PROJECT_UUID = UUID(PROJECT_ID)
SAFETY_RECORD_CODES = tuple(sorted({*SAFETY_RECORD_TYPES, *(code for code, _ in EXPECTED_REQUIREMENTS)}))
DatabaseCounts = Callable[[], dict[str, int]]


def _database_counts() -> dict[str, int]:
    with SessionLocal() as db:
        daily_sheets = list(
            db.scalars(
                select(FieldRecord).where(
                    FieldRecord.project_id == PROJECT_UUID,
                    FieldRecord.record_type == "daily_timesheet",
                    FieldRecord.status != "void",
                )
            ).all()
        )
        generated_reports = list(
            db.scalars(
                select(Document).where(
                    Document.project_id == PROJECT_UUID,
                    Document.category == "other",
                )
            ).all()
        )
        return {
            "daily_sheets": len(daily_sheets),
            "production_posts": sum(bool((item.details or {}).get("production_post")) for item in daily_sheets),
            "time_entries": int(
                db.scalar(select(func.count(TimeEntry.id)).where(TimeEntry.project_id == PROJECT_UUID)) or 0
            ),
            "generated_daily_reports": sum(
                (item.metadata_json or {}).get("source") == "daily_timesheet" for item in generated_reports
            ),
            "field_photo_references": sum(
                len((item.details or {}).get("photo_document_ids") or []) for item in daily_sheets
            ),
            "ticket_evidence_references": sum(
                len((item.details or {}).get("ticket_document_ids") or []) for item in daily_sheets
            ),
            "project_safety_records": int(
                db.scalar(
                    select(func.count(FieldRecord.id)).where(
                        FieldRecord.project_id == PROJECT_UUID,
                        FieldRecord.record_type.in_(SAFETY_RECORD_CODES),
                    )
                )
                or 0
            ),
            "completed_start_controls": int(
                db.scalar(
                    select(func.count(ProjectStartChecklistItem.id)).where(
                        ProjectStartChecklistItem.project_id == PROJECT_UUID,
                        ProjectStartChecklistItem.completed.is_(True),
                    )
                )
                or 0
            ),
        }


def _verify_dashboard(dashboard: dict[str, Any]) -> None:
    expected: dict[str, Any] = {
        "job_number": JOB_NUMBER,
        "mobilization_status": "not_ready",
        "checklist_completed_count": 0,
        "baseline_budget_total": EXPECTED_BUDGET,
        "budget_entry_count": 5,
        "procurement_requirement_count": 4,
        "procurement_plan_status": "draft",
        "po_request_count": 0,
        "pending_po_request_count": 0,
        "safety_release_status": "blocked",
        "portal_access_status": "not_started",
        "portal_assignment_count": 0,
        "production_posting_status": "blocked",
        "production_blockers": EXPECTED_BLOCKERS,
        "daily_sheet_count": 0,
        "production_post_count": 0,
        "latest_daily_sheet_status": "not_started",
        "field_production_folder_status": "not_initialized",
    }
    actual = {
        **{key: dashboard.get(key) for key in expected},
        "baseline_budget_total": _money(dashboard.get("baseline_budget_total")),
    }
    mismatches = {
        key: {"actual": actual.get(key), "expected": value}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if mismatches:
        raise ImportValidationError(f"Bennett production gate dashboard mismatch: {mismatches}")


def _verify_workspace(workspace: dict[str, Any]) -> None:
    production_entries = [
        entry
        for entry in workspace.get("entries") or []
        if str(entry.get("path") or "").endswith(PRODUCTION_FOLDER_SUFFIX)
    ]
    if production_entries:
        raise ImportValidationError("Bennett field-production folders exist before an approved production post.")


def run_pilot(
    api: Api,
    *,
    operator: str,
    email: str,
    password: str,
    count_records: DatabaseCounts = _database_counts,
) -> dict[str, Any]:
    readiness = _require_value(api.request("/readiness"), "Readiness")
    api.request(
        "/api/v1/auth/login",
        method="POST",
        body={"email": email, "password": password},
    )
    authenticated = _require_value(api.request("/api/v1/auth/me"), "Authenticated user")
    authenticated_user = authenticated.get("user") or authenticated
    if authenticated_user.get("role") not in {"admin", "operations_manager"}:
        raise ImportValidationError("Authenticated staging user lacks production-gate access.")

    before_counts = count_records()
    if any(before_counts.values()):
        raise ImportValidationError(
            "Bennett already has field-production, safety, or mobilization records; "
            f"the zero-state staging gate is blocked: {before_counts}"
        )

    project = _require_value(api.request(f"/api/v1/projects/{PROJECT_ID}"), "Bennett project")
    quote = _require_value(api.request(f"/api/v1/customer-quotes/{QUOTE_ID}"), "Bennett quote")
    workspaces = _require_value(
        api.request(f"/api/v1/estimates/workspace/project/{PROJECT_ID}"),
        "Bennett workspaces",
    )
    matches = [item for item in workspaces.get("items", []) if str(item.get("id")) == WORKSPACE_ID]
    if len(matches) != 1:
        raise ImportValidationError("Expected one exact Bennett concrete estimate workspace.")
    _verify_exact_source(project, matches[0], quote)
    _verify_procurement_plan(project)
    _verify_safety_launch((project.get("metadata") or {}).get("safety_launch") or {})

    financial = _require_value(
        api.request(f"/api/v1/finance/projects/{PROJECT_ID}"),
        "Bennett financial baseline",
    )
    budget_entries = _verify_financial_summary(financial)
    dashboard = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}/launch-dashboard"),
        "Bennett launch dashboard",
    )
    _verify_dashboard(dashboard)
    workspace = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}/workspace"),
        "Bennett awarded workspace",
    )
    _verify_workspace(workspace)

    bootstrap = _require_value(
        api.request("/api/v1/daily-timesheets/bootstrap"),
        "Daily timesheet bootstrap",
    )
    bennett_sheets = [
        item
        for item in bootstrap.get("sheets") or []
        if str(item.get("project_id")) == PROJECT_ID and item.get("status") != "void"
    ]
    if bennett_sheets:
        raise ImportValidationError("Bennett contains a Day 1/Day 2 daily sheet outside this read-only gate.")

    after_counts = count_records()
    if after_counts != before_counts:
        raise ImportValidationError(
            "Bennett production-gate verification changed protected records: "
            f"before={before_counts}, after={after_counts}"
        )
    api.request("/api/v1/auth/logout", method="POST", expected_status=204)
    return {
        "status": "passed",
        "pilot": "bennett_field_production_gate",
        "approval_boundary": APPROVAL_BOUNDARY,
        "operator": operator,
        "authenticated_as": authenticated_user.get("email"),
        "authenticated_role": authenticated_user.get("role"),
        "release_id": (readiness.get("checks") or {}).get("release_id"),
        "project": {"id": PROJECT_ID, "job_number": JOB_NUMBER, "status": "awarded"},
        "workspace": {"id": WORKSPACE_ID},
        "budget": {"total": EXPECTED_BUDGET, "entry_count": len(budget_entries)},
        "procurement": {"status": "draft", "requirement_count": 4},
        "safety_release_status": "blocked",
        "portal_access": {"status": "not_started", "assignment_count": 0},
        "mobilization_status": "not_ready",
        "production_posting_status": "blocked",
        "production_blockers": EXPECTED_BLOCKERS,
        "daily_sheet_count": after_counts["daily_sheets"],
        "production_post_count": after_counts["production_posts"],
        "generated_daily_report_count": after_counts["generated_daily_reports"],
        "time_entry_count": after_counts["time_entries"],
        "field_photo_count": after_counts["field_photo_references"],
        "ticket_evidence_count": after_counts["ticket_evidence_references"],
        "field_production_folder_status": "not_initialized",
        "commitments_created": 0,
        "po_requests_created": 0,
        "actuals_created": 0,
        "external_issuance_performed": False,
        "production_mutation_performed": False,
        "verified_at": datetime.now(UTC).isoformat(),
    }


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Verify the Bennett field-production gate in staging.")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--base-url", default=STAGING_BASE_URL)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    if settings.environment != "staging":
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "issues": ["This production-gate pilot is staging-only."],
                },
                indent=2,
            )
        )
        raise SystemExit(2)
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not email or not password:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "issues": ["Staging administrator credentials are unavailable."],
                },
                indent=2,
            )
        )
        raise SystemExit(2)
    try:
        report = run_pilot(
            ApiClient(args.base_url),
            operator=args.operator.strip(),
            email=email,
            password=password,
        )
    except (ImportValidationError, OSError, ValueError) as error:
        print(json.dumps({"status": "blocked", "issues": [str(error)]}, indent=2))
        raise SystemExit(2) from error
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
