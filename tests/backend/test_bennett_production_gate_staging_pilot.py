from copy import deepcopy

import pytest

from app.services.drive_tender_import import ImportValidationError
from app.tools.bennett_cost_budget_staging_pilot import (
    JOB_NUMBER,
    PROJECT_ID,
    STAGING_BASE_URL,
)
from app.tools.bennett_production_gate_staging_pilot import (
    APPROVAL_BOUNDARY,
    EXPECTED_BLOCKERS,
    _parser,
    run_pilot,
)
from test_bennett_safety_launch_staging_pilot import COUNTS, SafetyFakeApi


PRODUCTION_COUNTS = {
    **COUNTS,
    "daily_sheets": 0,
    "production_posts": 0,
    "time_entries": 0,
    "generated_daily_reports": 0,
    "field_photo_references": 0,
    "ticket_evidence_references": 0,
}
PRODUCTION_COUNTS.pop("user_accounts")
PRODUCTION_COUNTS.pop("employees")
PRODUCTION_COUNTS.pop("onboarding_records")


class ProductionGateFakeApi(SafetyFakeApi):
    def __init__(self) -> None:
        super().__init__(already_initialized=True)

    def request(self, path: str, **kwargs):
        if path == f"/api/v1/projects/{PROJECT_ID}/launch-dashboard":
            self.calls.append(
                (
                    path,
                    kwargs.get("method", "GET"),
                    kwargs.get("body"),
                    kwargs.get("expected_status", 200),
                )
            )
            return {
                "job_number": JOB_NUMBER,
                "mobilization_status": "not_ready",
                "checklist_completed_count": 0,
                "baseline_budget_total": "26660.93",
                "budget_entry_count": 5,
                "procurement_requirement_count": 4,
                "procurement_plan_status": "draft",
                "po_request_count": 0,
                "pending_po_request_count": 0,
                "safety_release_status": "blocked",
                "portal_access_status": "not_started",
                "portal_assignment_count": 0,
                "production_posting_status": "blocked",
                "production_blockers": deepcopy(EXPECTED_BLOCKERS),
                "daily_sheet_count": 0,
                "production_post_count": 0,
                "latest_daily_sheet_status": "not_started",
                "field_production_folder_status": "not_initialized",
            }
        if path == "/api/v1/daily-timesheets/bootstrap":
            self.calls.append(
                (
                    path,
                    kwargs.get("method", "GET"),
                    kwargs.get("body"),
                    kwargs.get("expected_status", 200),
                )
            )
            return {"sheets": []}
        return super().request(path, **kwargs)


def test_cli_defaults_to_secure_live_staging_origin() -> None:
    args = _parser().parse_args(["--operator", "GitHub staging production gate"])

    assert args.base_url == STAGING_BASE_URL
    assert args.base_url == "https://staging.os.ironhousecivil.com"


def test_production_gate_is_exact_read_only_and_zero_state() -> None:
    api = ProductionGateFakeApi()

    report = run_pilot(
        api,
        operator="GitHub staging production gate",
        email="admin@ironhousecontracting.com",
        password="not-recorded",
        count_records=lambda: deepcopy(PRODUCTION_COUNTS),
    )

    assert report["status"] == "passed"
    assert report["approval_boundary"] == APPROVAL_BOUNDARY
    assert report["project"] == {
        "id": PROJECT_ID,
        "job_number": JOB_NUMBER,
        "status": "awarded",
    }
    assert report["production_posting_status"] == "blocked"
    assert report["production_blockers"] == EXPECTED_BLOCKERS
    assert report["daily_sheet_count"] == 0
    assert report["production_post_count"] == 0
    assert report["generated_daily_report_count"] == 0
    assert report["time_entry_count"] == 0
    assert report["field_photo_count"] == 0
    assert report["ticket_evidence_count"] == 0
    assert report["field_production_folder_status"] == "not_initialized"
    assert report["actuals_created"] == 0
    assert report["external_issuance_performed"] is False
    assert report["production_mutation_performed"] is False
    assert "not-recorded" not in str(report)

    business_calls = [
        call for call in api.calls if call[0] not in {"/api/v1/auth/login", "/api/v1/auth/logout"}
    ]
    assert all(method == "GET" for _, method, _, _ in business_calls)
    assert not any(
        path.endswith("/post") or path.endswith("/safety-launch") for path, *_ in api.calls
    )


def test_production_gate_fails_closed_if_a_daily_sheet_exists() -> None:
    api = ProductionGateFakeApi()
    changed = {**PRODUCTION_COUNTS, "daily_sheets": 1}

    with pytest.raises(ImportValidationError, match="zero-state staging gate"):
        run_pilot(
            api,
            operator="GitHub staging production gate",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
            count_records=lambda: deepcopy(changed),
        )

    assert not any(path.startswith(f"/api/v1/projects/{PROJECT_ID}") for path, *_ in api.calls)
