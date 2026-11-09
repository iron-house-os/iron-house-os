from copy import deepcopy
from typing import Any

import pytest

from app.services.bennett_strata_staging_import import PROJECT_NAME, SOURCE_KEY, SOURCE_REVISION
from app.services.drive_tender_import import ImportValidationError
from app.tools.bennett_cost_budget_staging_pilot import (
    BUDGET_REQUEST,
    EXPECTED_CODES,
    JOB_NUMBER,
    PROJECT_ID,
    QUOTE_ID,
    STAGING_BASE_URL,
    WORKSPACE_ID,
    _parser,
    run_pilot,
)
from app.tools.bennett_procurement_staging_pilot import (
    EXPECTED_REQUIREMENTS,
    PROCUREMENT_REQUEST,
    _parser as procurement_parser,
    run_pilot as run_procurement_pilot,
)


def test_cli_defaults_to_secure_live_staging_origin() -> None:
    args = _parser().parse_args(["--operator", "GitHub staging budget"])

    assert args.base_url == STAGING_BASE_URL
    assert args.base_url == "https://staging.os.ironhousecivil.com"


class FakeApi:
    def __init__(self, *, already_budgeted: bool = False, already_planned: bool = False) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None, int]] = []
        self.project = {
            "id": PROJECT_ID,
            "name": PROJECT_NAME,
            "status": "awarded",
            "project_number": JOB_NUMBER,
            "contract_value": "38080.00",
            "metadata": {
                SOURCE_KEY: {"latest_source_revision": SOURCE_REVISION},
                "award_pricing_baseline": {
                    "source_quote_id": QUOTE_ID,
                    "source_quote_number": "Q-2026-002",
                    "pricing_subtotal": "36266.67",
                    "cost_budget_status": "needs_cost_allocation",
                    "lines": [{"description": "Concrete pull and pour", "cost_code": None}],
                },
                "procurement_plan": {
                    "status": "draft",
                    "automatic_commitment": False,
                    "requirements": [
                        {"description": "Concrete", "po_number": None, "approval": None}
                    ],
                },
            },
        }
        self.workspace = {
            "id": WORKSPACE_ID,
            "estimate": {
                "source": SOURCE_KEY,
                "source_revision": SOURCE_REVISION,
                "estimate_key": "concrete",
                "summary": {
                    "direct_cost": "21910.93",
                    "risk_cost": "4750.00",
                },
            },
        }
        self.quote = {
            "id": QUOTE_ID,
            "quote_number": "Q-2026-002",
            "status": "accepted",
            "issue_status": "draft",
            "job_number": JOB_NUMBER,
            "subtotal": "36266.67",
            "total": "38080.00",
            "issued_at": None,
        }
        self.entries: list[dict[str, Any]] = []
        if already_budgeted or already_planned:
            self._apply_budget()
        if already_planned:
            self._apply_procurement()

    def _apply_budget(self) -> None:
        if self.entries:
            return
        specs = [
            ("line-001", "4100", "19860.93"),
            ("line-002", "5100", "200.00"),
            ("line-003", "5110", "1100.00"),
            ("line-004", "6100", "750.00"),
            ("risk", "4100", "4750.00"),
        ]
        self.entries = [
            {
                "id": f"00000000-0000-0000-0000-00000000000{index}",
                "project_id": PROJECT_ID,
                "cost_code": code,
                "entry_type": "budget",
                "amount": amount,
                "status": "posted",
                "source_type": "estimate_workspace",
                "source_id": WORKSPACE_ID,
                "source_key": f"estimate-budget:{WORKSPACE_ID}:{position}",
            }
            for index, (position, code, amount) in enumerate(specs, start=1)
        ]
        baseline = self.project["metadata"]["award_pricing_baseline"]
        baseline.update(
            {
                "cost_budget_status": "allocated",
                "cost_budget_source_workspace_id": WORKSPACE_ID,
                "cost_budget_total": "26660.93",
                "cost_budget_lines": [
                    {"cost_code": item["cost_code"], "amount": item["amount"]}
                    for item in self.entries
                ],
            }
        )
        self.project["metadata"]["project_cost_codes"] = [
            {"code": code, "name": values["name"]}
            for code, values in EXPECTED_CODES.items()
        ]

    def _apply_procurement(self) -> None:
        positions = {
            "CON-001": "line-001",
            "EQP-001": "line-002",
            "EQP-002": "line-003",
            "TRK-001": "line-004",
        }
        names = {"4100": "Concrete restoration", "5100": "Small equipment rental", "5110": "Skid steer / hydraulic attachment", "6100": "Trucking, disposal and material hauling"}
        self.project["metadata"]["procurement_plan"] = {
            "source_quote_id": QUOTE_ID,
            "source_estimate_workspace_id": WORKSPACE_ID,
            "job_number": JOB_NUMBER,
            "status": "draft",
            "automatic_commitment": False,
            "requirements": [
                {
                    **expected,
                    "requirement_id": f"estimate-procurement:{WORKSPACE_ID}:{expected['source_code']}",
                    "source_type": "estimate_workspace",
                    "source_estimate_workspace_id": WORKSPACE_ID,
                    "source_budget_key": f"estimate-budget:{WORKSPACE_ID}:{positions[expected['source_code']]}",
                    "job_number": JOB_NUMBER,
                    "cost_code_name": names[expected["cost_code"]],
                    "description": request["description"],
                    "specification": request.get("specification"),
                    "vendor_id": None,
                    "vendor_quote_reference": None,
                    "required_on_site_date": None,
                    "approval": None,
                    "po_number": None,
                    "commitment_created": False,
                }
                for expected, request in zip(
                    EXPECTED_REQUIREMENTS,
                    PROCUREMENT_REQUEST["procurement_requirements"],
                    strict=True,
                )
            ],
        }

    def _financial_summary(self) -> dict[str, Any]:
        return {
            "project_id": PROJECT_ID,
            "contract_value": "38080.00",
            "budget": "26660.93" if self.entries else "0.00",
            "committed": "0.00",
            "actual": "0.00",
            "forecast_cost": "0.00",
            "entries": deepcopy(self.entries),
        }

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any] | None:
        self.calls.append((path, method, body, expected_status))
        if path == "/readiness":
            return {"checks": {"release_id": "b" * 40}}
        if path == "/api/v1/auth/login":
            return {"user": {"email": "admin@ironhousecontracting.com", "role": "admin"}}
        if path == "/api/v1/auth/me":
            return {"user": {"email": "admin@ironhousecontracting.com", "role": "admin"}}
        if path == f"/api/v1/projects/{PROJECT_ID}":
            return deepcopy(self.project)
        if path == f"/api/v1/customer-quotes/{QUOTE_ID}":
            return deepcopy(self.quote)
        if path == f"/api/v1/estimates/workspace/project/{PROJECT_ID}":
            return {"items": [deepcopy(self.workspace)], "total": 1}
        if path == f"/api/v1/finance/projects/{PROJECT_ID}" and method == "GET":
            return self._financial_summary()
        if path == f"/api/v1/finance/projects/{PROJECT_ID}/import-estimate":
            assert method == "POST"
            self._apply_budget()
            if body == PROCUREMENT_REQUEST:
                self._apply_procurement()
            else:
                assert body == BUDGET_REQUEST
            return self._financial_summary()
        if path == f"/api/v1/projects/{PROJECT_ID}/launch-dashboard":
            return {
                "job_number": JOB_NUMBER,
                "mobilization_status": "not_ready",
                "checklist_completed_count": 0,
                "baseline_budget_total": "26660.93",
                "budget_entry_count": 5,
                "award_baseline_source": "Q-2026-002",
                "award_pricing_subtotal": "36266.67",
                "award_cost_budget_status": "allocated",
                "uncoded_award_line_count": 0,
                "procurement_plan_status": "draft",
                "procurement_requirement_count": len(
                    self.project["metadata"]["procurement_plan"]["requirements"]
                ),
                "po_request_count": 0,
                "pending_po_request_count": 0,
            }
        if path == "/api/v1/daily-timesheets/bootstrap":
            return {
                "project_cost_codes": {
                    PROJECT_ID: deepcopy(self.project["metadata"]["project_cost_codes"])
                }
            }
        if path == "/api/v1/auth/logout":
            return None
        raise AssertionError(f"Unexpected request: {method} {path}")


@pytest.mark.parametrize(
    ("already_budgeted", "expected_action"),
    [(False, "create_original_cost_budget"), (True, "reuse_existing_cost_budget")],
)
def test_budget_pilot_is_exact_safe_and_idempotent(
    already_budgeted: bool,
    expected_action: str,
) -> None:
    api = FakeApi(already_budgeted=already_budgeted)

    report = run_pilot(
        api,
        operator="GitHub staging budget",
        email="admin@ironhousecontracting.com",
        password="not-recorded",
    )

    assert report["status"] == "passed"
    assert report["approval_boundary"] == "staging_original_budget_only_no_commitments"
    assert report["transition_action"] == expected_action
    assert report["project"] == {
        "id": PROJECT_ID,
        "job_number": JOB_NUMBER,
        "status": "awarded",
    }
    assert report["budget"]["total"] == "26660.93"
    assert report["budget"]["entry_count"] == 5
    assert report["idempotent_retry"] is True
    assert report["commitments_created"] == 0
    assert report["actuals_created"] == 0
    assert report["po_requests_created"] == 0
    assert report["checklist_items_completed"] == 0
    assert report["external_issuance_performed"] is False
    assert report["production_mutation_performed"] is False
    assert "not-recorded" not in str(report)

    imports = [call for call in api.calls if call[0].endswith("/import-estimate")]
    assert len(imports) == 2
    assert all(call[1] == "POST" and call[2] == BUDGET_REQUEST for call in imports)
    assert not any("purchase-orders" in path or "quickbooks" in path for path, *_ in api.calls)


def test_budget_pilot_fails_closed_on_job_number_drift() -> None:
    api = FakeApi()
    api.project["project_number"] = "IH2026999"

    with pytest.raises(ImportValidationError, match="source mismatch"):
        run_pilot(
            api,
            operator="GitHub staging budget",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
        )

    assert not any(path.endswith("/import-estimate") for path, *_ in api.calls)


def test_budget_pilot_fails_closed_on_existing_commitment() -> None:
    api = FakeApi()
    original = api._financial_summary

    def summary_with_commitment() -> dict[str, Any]:
        summary = original()
        summary["committed"] = "100.00"
        return summary

    api._financial_summary = summary_with_commitment  # type: ignore[method-assign]

    with pytest.raises(ImportValidationError, match="commitments or actuals"):
        run_pilot(
            api,
            operator="GitHub staging budget",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
        )

    assert not any(path.endswith("/import-estimate") for path, *_ in api.calls)


def test_procurement_cli_defaults_to_secure_live_staging_origin() -> None:
    args = procurement_parser().parse_args(["--operator", "GitHub staging procurement"])

    assert args.base_url == STAGING_BASE_URL
    assert args.base_url == "https://staging.os.ironhousecivil.com"


@pytest.mark.parametrize(
    ("already_planned", "expected_action"),
    [
        (False, "replace_safe_quote_procurement_shell"),
        (True, "reuse_existing_procurement_plan"),
    ],
)
def test_procurement_pilot_is_exact_safe_and_idempotent(
    already_planned: bool,
    expected_action: str,
) -> None:
    api = FakeApi(already_budgeted=True, already_planned=already_planned)

    report = run_procurement_pilot(
        api,
        operator="GitHub staging procurement",
        email="admin@ironhousecontracting.com",
        password="not-recorded",
    )

    assert report["status"] == "passed"
    assert report["approval_boundary"] == "staging_procurement_planning_only_no_commitments"
    assert report["transition_action"] == expected_action
    assert report["project"]["job_number"] == JOB_NUMBER
    assert report["budget"] == {"total": "26660.93", "entry_count": 5}
    assert report["procurement"]["status"] == "draft"
    assert report["procurement"]["requirement_count"] == 4
    assert report["procurement"]["ready_mix_order_quantity_confirmed"] is False
    assert report["idempotent_retry"] is True
    assert report["vendors_selected"] == 0
    assert report["commitments_created"] == 0
    assert report["po_requests_created"] == 0
    assert report["actuals_created"] == 0
    assert report["checklist_items_completed"] == 0
    assert report["external_issuance_performed"] is False
    assert report["production_mutation_performed"] is False
    assert "not-recorded" not in str(report)

    imports = [call for call in api.calls if call[0].endswith("/import-estimate")]
    assert len(imports) == 2
    assert all(call[1] == "POST" and call[2] == PROCUREMENT_REQUEST for call in imports)
    assert not any("purchase-orders" in path or "quickbooks" in path for path, *_ in api.calls)


def test_procurement_pilot_fails_closed_on_vendor_selection() -> None:
    api = FakeApi(already_planned=True)
    api.project["metadata"]["procurement_plan"]["requirements"][1]["vendor_id"] = "vendor-1"

    with pytest.raises(ImportValidationError, match="decision or commitment"):
        run_procurement_pilot(
            api,
            operator="GitHub staging procurement",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
        )

    assert not any(path.endswith("/import-estimate") for path, *_ in api.calls)
