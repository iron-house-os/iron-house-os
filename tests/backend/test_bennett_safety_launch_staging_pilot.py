from copy import deepcopy
from typing import Any

import pytest

from app.services.drive_tender_import import ImportValidationError
from app.tools.bennett_cost_budget_staging_pilot import JOB_NUMBER, PROJECT_ID, STAGING_BASE_URL
from app.tools.bennett_safety_launch_staging_pilot import (
    EXPECTED_REQUIREMENTS,
    _parser,
    run_pilot,
)
from test_bennett_cost_budget_staging_pilot import FakeApi


COUNTS = {
    "user_accounts": 3,
    "employees": 8,
    "onboarding_records": 2,
    "project_safety_records": 0,
    "completed_start_controls": 0,
}


class SafetyFakeApi(FakeApi):
    def __init__(self, *, already_initialized: bool = False) -> None:
        super().__init__(already_planned=True)
        self.workspace_root = f"{JOB_NUMBER}_BennettStrataConcreteRestoration"
        self.workspace_manifest = {
            "project_id": PROJECT_ID,
            "job_number": JOB_NUMBER,
            "root_folder": self.workspace_root,
            "provisioned_at": "2026-08-28T00:00:00Z",
            "project_index": "# Project Index",
            "entries": [
                {
                    "path": f"{self.workspace_root}/13_Award_Handoff",
                    "kind": "folder",
                    "description": "Award handoff package.",
                }
            ],
        }
        if already_initialized:
            self._apply_safety_launch()

    def _apply_safety_launch(self) -> dict[str, Any]:
        existing = self.project["metadata"].get("safety_launch")
        if existing:
            return existing
        folder_path = f"{self.workspace_root}/13_Award_Handoff/Safety"
        launch = {
            "project_id": PROJECT_ID,
            "job_number": JOB_NUMBER,
            "release_status": "blocked",
            "folder_path": folder_path,
            "folder_status": "prepared",
            "record_requirements": [
                {
                    "code": code,
                    "label": label,
                    "applicability_status": "unconfirmed",
                    "status": "not_started",
                    "record_id": None,
                    "evidence_document_ids": [],
                }
                for code, label in EXPECTED_REQUIREMENTS
            ],
            "portal_access": {
                "status": "not_started",
                "automatic_provisioning": False,
                "assignments": [],
            },
            "initialized_by": "admin@ironhousecontracting.com",
            "initialized_at": "2026-08-28T03:30:00Z",
        }
        self.project["metadata"]["safety_launch"] = launch
        self.workspace_manifest["entries"].append(
            {
                "path": folder_path,
                "kind": "folder",
                "description": "Internal project safety launch records; prepared path only and not safety evidence.",
            }
        )
        return launch

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any] | None:
        if path == f"/api/v1/projects/{PROJECT_ID}/safety-launch":
            self.calls.append((path, method, body, expected_status))
            assert method == "POST"
            assert expected_status == 201
            return deepcopy(self._apply_safety_launch())
        if path == f"/api/v1/projects/{PROJECT_ID}/workspace":
            self.calls.append((path, method, body, expected_status))
            return deepcopy(self.workspace_manifest)
        if path == f"/api/v1/projects/{PROJECT_ID}/launch-dashboard":
            self.calls.append((path, method, body, expected_status))
            launch = self.project["metadata"].get("safety_launch") or {}
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
                "safety_record_counts": {
                    "safety_permit": 0,
                    "emergency_action_card": 0,
                    "daily_hazard_assessment": 0,
                    "toolbox_talk": 0,
                    "corrective_action": 0,
                },
                "safety_release_status": launch.get("release_status", "not_initialized"),
                "safety_requirement_count": len(launch.get("record_requirements") or []),
                "safety_folder_status": launch.get("folder_status", "not_initialized"),
                "portal_access_status": (launch.get("portal_access") or {}).get(
                    "status", "not_initialized"
                ),
                "portal_assignment_count": len(
                    (launch.get("portal_access") or {}).get("assignments") or []
                ),
            }
        return super().request(
            path,
            method=method,
            body=body,
            expected_status=expected_status,
        )


def test_cli_defaults_to_secure_live_staging_origin() -> None:
    args = _parser().parse_args(["--operator", "GitHub staging safety launch"])

    assert args.base_url == STAGING_BASE_URL
    assert args.base_url == "https://staging.os.ironhousecivil.com"


@pytest.mark.parametrize(
    ("already_initialized", "expected_action"),
    [
        (False, "initialize_blocked_safety_launch"),
        (True, "reuse_existing_blocked_safety_launch"),
    ],
)
def test_safety_launch_pilot_is_exact_blocked_and_idempotent(
    already_initialized: bool,
    expected_action: str,
) -> None:
    api = SafetyFakeApi(already_initialized=already_initialized)

    report = run_pilot(
        api,
        operator="GitHub staging safety launch",
        email="admin@ironhousecontracting.com",
        password="not-recorded",
        count_records=lambda: deepcopy(COUNTS),
    )

    assert report["status"] == "passed"
    assert report["approval_boundary"] == "staging_safety_shell_only_no_release_or_access"
    assert report["transition_action"] == expected_action
    assert report["project"] == {
        "id": PROJECT_ID,
        "job_number": JOB_NUMBER,
        "status": "awarded",
    }
    assert report["budget"] == {"total": "26660.93", "entry_count": 5}
    assert report["procurement"] == {"status": "draft", "requirement_count": 4}
    assert report["safety_launch"] == {
        "release_status": "blocked",
        "requirement_count": 6,
        "folder_status": "prepared",
        "actual_safety_record_count": 0,
    }
    assert report["portal_access"] == {
        "status": "not_started",
        "assignment_count": 0,
        "automatic_provisioning": False,
    }
    assert report["idempotent_retry"] is True
    assert report["portal_accounts_created"] == 0
    assert report["employees_created"] == 0
    assert report["onboarding_records_created"] == 0
    assert report["checklist_items_completed"] == 0
    assert report["commitments_created"] == 0
    assert report["po_requests_created"] == 0
    assert report["actuals_created"] == 0
    assert report["external_issuance_performed"] is False
    assert report["production_mutation_performed"] is False
    assert "not-recorded" not in str(report)

    initializations = [call for call in api.calls if call[0].endswith("/safety-launch")]
    assert len(initializations) == 2
    assert all(call[1] == "POST" and call[3] == 201 for call in initializations)
    assert not any("employees" in path or "invitations" in path for path, *_ in api.calls)


def test_safety_launch_pilot_fails_closed_on_existing_portal_assignment() -> None:
    api = SafetyFakeApi(already_initialized=True)
    api.project["metadata"]["safety_launch"]["portal_access"] = {
        "status": "active",
        "automatic_provisioning": False,
        "assignments": [
            {
                "employee_id": "00000000-0000-0000-0000-000000000999",
                "portal_role": "foreman",
                "status": "active",
            }
        ],
    }

    with pytest.raises(ImportValidationError, match="portal access"):
        run_pilot(
            api,
            operator="GitHub staging safety launch",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
            count_records=lambda: deepcopy(COUNTS),
        )

    assert not any(path.endswith("/safety-launch") for path, *_ in api.calls)
