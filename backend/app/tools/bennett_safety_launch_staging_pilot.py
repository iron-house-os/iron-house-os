"""Initialize and verify the blocked Bennett safety and portal launch shell in staging."""

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
from app.models.employee_onboarding import EmployeeOnboarding
from app.models.field_operations import FieldRecord
from app.models.project import ProjectStartChecklistItem
from app.models.user import Employee, UserAccount
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


SAFETY_FOLDER_SUFFIX = "/13_Award_Handoff/Safety"
EXPECTED_REQUIREMENTS = [
    ("project_safety_plan", "Project-specific safety plan"),
    ("emergency_action_card", "Emergency action card"),
    ("field_hazard_assessment", "Field-level hazard assessment"),
    ("toolbox_talk", "Crew toolbox talk"),
    ("safety_permit", "Task permit or safety-control record, if applicable"),
    ("orientation_verification", "Crew orientation and qualification verification"),
]
DatabaseCounts = Callable[[], dict[str, int]]
PROJECT_UUID = UUID(PROJECT_ID)


def _database_counts() -> dict[str, int]:
    with SessionLocal() as db:
        return {
            "user_accounts": int(db.scalar(select(func.count(UserAccount.id))) or 0),
            "employees": int(db.scalar(select(func.count(Employee.id))) or 0),
            "onboarding_records": int(
                db.scalar(select(func.count(EmployeeOnboarding.id))) or 0
            ),
            "project_safety_records": int(
                db.scalar(
                    select(func.count(FieldRecord.id)).where(
                        FieldRecord.project_id == PROJECT_UUID,
                        FieldRecord.record_type.in_(SAFETY_RECORD_TYPES),
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


def _verify_safety_launch(launch: dict[str, Any]) -> None:
    expected = {
        "project_id": PROJECT_ID,
        "job_number": JOB_NUMBER,
        "release_status": "blocked",
        "folder_status": "prepared",
    }
    mismatches = {
        key: {"actual": str(launch.get(key)), "expected": value}
        for key, value in expected.items()
        if str(launch.get(key)) != value
    }
    if mismatches:
        raise ImportValidationError(f"Bennett safety launch mismatch: {mismatches}")
    if not str(launch.get("folder_path") or "").endswith(SAFETY_FOLDER_SUFFIX):
        raise ImportValidationError("Bennett safety launch uses the wrong internal folder path.")
    requirements = launch.get("record_requirements") or []
    actual_requirements = [
        (str(item.get("code") or ""), str(item.get("label") or ""))
        for item in requirements
    ]
    if actual_requirements != EXPECTED_REQUIREMENTS:
        raise ImportValidationError(
            f"Bennett safety launch requirements mismatch: {actual_requirements}"
        )
    if any(
        item.get("applicability_status") != "unconfirmed"
        or item.get("status") != "not_started"
        or item.get("record_id") is not None
        or item.get("evidence_document_ids") not in (None, [])
        for item in requirements
    ):
        raise ImportValidationError("Bennett safety requirements contain inferred facts or evidence.")
    portal = launch.get("portal_access") or {}
    if portal != {
        "status": "not_started",
        "automatic_provisioning": False,
        "assignments": [],
    }:
        raise ImportValidationError("Bennett portal access was assigned or activated.")


def _verify_workspace(workspace: dict[str, Any], folder_path: str) -> None:
    entries = workspace.get("entries") or []
    matches = [
        entry
        for entry in entries
        if entry.get("path") == folder_path and entry.get("kind") == "folder"
    ]
    if len(matches) != 1:
        raise ImportValidationError("Bennett internal safety folder was not prepared exactly once.")


def _verify_dashboard(api: Api) -> dict[str, Any]:
    dashboard = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}/launch-dashboard"),
        "Bennett launch dashboard",
    )
    expected = {
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
        "safety_requirement_count": len(EXPECTED_REQUIREMENTS),
        "safety_folder_status": "prepared",
        "portal_access_status": "not_started",
        "portal_assignment_count": 0,
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
        raise ImportValidationError(f"Bennett safety launch dashboard mismatch: {mismatches}")
    safety_counts = dashboard.get("safety_record_counts") or {}
    if any(int(safety_counts.get(record_type) or 0) != 0 for record_type in SAFETY_RECORD_TYPES):
        raise ImportValidationError("Bennett safety evidence was created during launch initialization.")
    return dashboard


def run_pilot(
    api: Api,
    *,
    operator: str,
    email: str,
    password: str,
    count_records: DatabaseCounts = _database_counts,
) -> dict[str, Any]:
    readiness = _require_value(api.request("/readiness"), "Readiness")
    api.request("/api/v1/auth/login", method="POST", body={"email": email, "password": password})
    authenticated = _require_value(api.request("/api/v1/auth/me"), "Authenticated user")
    authenticated_user = authenticated.get("user") or authenticated
    if authenticated_user.get("role") not in {"admin", "operations_manager"}:
        raise ImportValidationError("Authenticated staging user lacks safety launch access.")

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
    financial = _require_value(
        api.request(f"/api/v1/finance/projects/{PROJECT_ID}"),
        "Bennett financial baseline",
    )
    entries = _verify_financial_summary(financial)
    before_counts = count_records()
    if before_counts.get("project_safety_records") != 0:
        raise ImportValidationError("Bennett already has safety evidence; automated initialization is blocked.")
    if before_counts.get("completed_start_controls") != 0:
        raise ImportValidationError("Bennett start controls progressed before safety launch initialization.")

    existing = (project.get("metadata") or {}).get("safety_launch")
    if existing is None:
        transition_action = "initialize_blocked_safety_launch"
    else:
        _verify_safety_launch(existing)
        transition_action = "reuse_existing_blocked_safety_launch"

    first = _require_value(
        api.request(
            f"/api/v1/projects/{PROJECT_ID}/safety-launch",
            method="POST",
            expected_status=201,
        ),
        "Initialized Bennett safety launch",
    )
    _verify_safety_launch(first)
    retry = _require_value(
        api.request(
            f"/api/v1/projects/{PROJECT_ID}/safety-launch",
            method="POST",
            expected_status=201,
        ),
        "Retried Bennett safety launch",
    )
    _verify_safety_launch(retry)
    if first != retry:
        raise ImportValidationError("Bennett safety launch retry changed the blocked shell.")
    refreshed = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}"),
        "Bennett project after safety launch initialization",
    )
    _verify_safety_launch((refreshed.get("metadata") or {}).get("safety_launch") or {})
    workspace = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}/workspace"),
        "Bennett awarded workspace",
    )
    _verify_workspace(workspace, str(first["folder_path"]))
    _verify_dashboard(api)

    after_counts = count_records()
    if after_counts != before_counts:
        raise ImportValidationError(
            f"Safety launch initialization changed protected employee, account, evidence, or checklist counts: before={before_counts}, after={after_counts}"
        )
    api.request("/api/v1/auth/logout", method="POST", expected_status=204)
    return {
        "status": "passed",
        "pilot": "bennett_blocked_safety_launch",
        "approval_boundary": "staging_safety_shell_only_no_release_or_access",
        "operator": operator,
        "authenticated_as": authenticated_user.get("email"),
        "authenticated_role": authenticated_user.get("role"),
        "release_id": (readiness.get("checks") or {}).get("release_id"),
        "transition_action": transition_action,
        "project": {"id": PROJECT_ID, "job_number": JOB_NUMBER, "status": "awarded"},
        "workspace": {"id": WORKSPACE_ID, "safety_folder": first["folder_path"]},
        "budget": {"total": EXPECTED_BUDGET, "entry_count": len(entries)},
        "procurement": {"status": "draft", "requirement_count": 4},
        "safety_launch": {
            "release_status": "blocked",
            "requirement_count": len(EXPECTED_REQUIREMENTS),
            "folder_status": "prepared",
            "actual_safety_record_count": after_counts["project_safety_records"],
        },
        "portal_access": {
            "status": "not_started",
            "assignment_count": 0,
            "automatic_provisioning": False,
        },
        "idempotent_retry": True,
        "portal_accounts_created": 0,
        "employees_created": 0,
        "onboarding_records_created": 0,
        "checklist_items_completed": 0,
        "commitments_created": 0,
        "po_requests_created": 0,
        "actuals_created": 0,
        "external_issuance_performed": False,
        "production_mutation_performed": False,
        "verified_at": datetime.now(UTC).isoformat(),
    }


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Initialize the blocked Bennett safety launch in staging.")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--base-url", default=STAGING_BASE_URL)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    if settings.environment != "staging":
        print(json.dumps({"status": "blocked", "issues": ["This safety launch pilot is staging-only."]}, indent=2))
        raise SystemExit(2)
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not email or not password:
        print(json.dumps({"status": "blocked", "issues": ["Staging administrator credentials are unavailable."]}, indent=2))
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
