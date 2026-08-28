from copy import deepcopy
from typing import Any

import pytest

from app.services.bennett_strata_staging_import import PROJECT_NAME, SOURCE_KEY, SOURCE_REVISION
from app.services.drive_tender_import import ImportValidationError
from app.tools.bennett_quote_staging_award import (
    ACCEPTANCE_NOTE,
    ACCEPTANCE_REFERENCE,
    PROJECT_ID,
    QUOTE_ID,
    STAGING_BASE_URL,
    WORKSPACE_ID,
    _parser,
    run_award,
)

JOB_NUMBER = "IH2026007"


def test_cli_defaults_to_secure_live_staging_origin() -> None:
    args = _parser().parse_args(["--operator", "GitHub staging award"])

    assert args.base_url == STAGING_BASE_URL
    assert args.base_url == "https://staging.os.ironhousecivil.com"


class FakeApi:
    def __init__(self, *, already_awarded: bool = False) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None, int]] = []
        self.project = {
            "id": PROJECT_ID,
            "name": PROJECT_NAME,
            "status": "opportunity",
            "project_number": None,
            "contract_value": None,
            "metadata": {SOURCE_KEY: {"latest_source_revision": SOURCE_REVISION}},
        }
        self.workspace = {
            "id": WORKSPACE_ID,
            "estimate": {
                "source": SOURCE_KEY,
                "source_revision": SOURCE_REVISION,
                "estimate_key": "concrete",
            },
        }
        self.quote = {
            "id": QUOTE_ID,
            "project_id": PROJECT_ID,
            "source_estimate_workspace_id": WORKSPACE_ID,
            "quote_number": "Q-2026-002",
            "customer_name": "Bennett Strata",
            "subtotal": "36266.67",
            "gst": "1813.33",
            "total": "38080.00",
            "status": "draft",
            "issue_status": "draft",
            "record_revision": 1,
            "job_number": None,
            "accepted_at": None,
            "accepted_by": None,
            "acceptance_reference": None,
            "acceptance_note": None,
            "issued_at": None,
        }
        if already_awarded:
            self._apply_award()

    def _apply_award(self) -> None:
        if self.quote["status"] == "accepted":
            return
        self.quote.update(
            {
                "status": "accepted",
                "record_revision": 2,
                "job_number": JOB_NUMBER,
                "accepted_at": "2026-08-28T01:30:00Z",
                "accepted_by": "admin@ironhousecontracting.com",
                "acceptance_reference": ACCEPTANCE_REFERENCE,
                "acceptance_note": ACCEPTANCE_NOTE,
            }
        )
        self.project.update(
            {
                "status": "awarded",
                "project_number": JOB_NUMBER,
                "contract_value": 38080.0,
            }
        )
        self.project["metadata"].update(
            {
                "award_pricing_baseline": {
                    "source_quote_id": QUOTE_ID,
                    "source_quote_number": "Q-2026-002",
                    "source_quote_revision": 2,
                    "pricing_subtotal": "36266.67",
                    "basis": "accepted_customer_quote_price",
                    "cost_budget_status": "needs_cost_allocation",
                    "lines": [
                        {
                            "description": "Concrete pull and pour",
                            "cost_code": None,
                            "cost_budget_amount": None,
                        }
                    ],
                },
                "procurement_plan": {
                    "source_quote_id": QUOTE_ID,
                    "status": "draft",
                    "automatic_commitment": False,
                    "requirements": [
                        {"description": "Concrete", "po_number": None, "approval": None}
                    ],
                },
            }
        )

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
        if path == f"/api/v1/projects/{PROJECT_ID}" and method == "GET":
            return deepcopy(self.project)
        if path == f"/api/v1/estimates/workspace/project/{PROJECT_ID}":
            return {"items": [deepcopy(self.workspace)], "total": 1}
        if path == f"/api/v1/customer-quotes/{QUOTE_ID}" and method == "GET":
            return deepcopy(self.quote)
        if path == f"/api/v1/customer-quotes/{QUOTE_ID}/accept":
            self._apply_award()
            return deepcopy(self.quote)
        if path == f"/api/v1/projects/{PROJECT_ID}/workspace":
            return {"job_number": JOB_NUMBER, "root_folder": f"{JOB_NUMBER}_BennettStrata"}
        if path == f"/api/v1/projects/{PROJECT_ID}/start-checklist":
            return {"status": "not_ready", "completed_count": 0, "total_count": 10}
        if path == f"/api/v1/projects/{PROJECT_ID}/launch-dashboard":
            return {
                "job_number": JOB_NUMBER,
                "mobilization_status": "not_ready",
                "award_baseline_source": "Q-2026-002",
                "award_pricing_subtotal": 36266.67,
                "award_cost_budget_status": "needs_cost_allocation",
                "uncoded_award_line_count": 1,
                "procurement_requirement_count": 1,
                "procurement_plan_status": "draft",
                "po_request_count": 0,
            }
        if path == "/api/v1/auth/logout":
            return None
        raise AssertionError(f"Unexpected request: {method} {path}")


@pytest.mark.parametrize(
    ("already_awarded", "expected_action"),
    [(False, "accept_and_award"), (True, "reuse_existing_award")],
)
def test_award_is_exact_safe_and_idempotent(already_awarded: bool, expected_action: str) -> None:
    api = FakeApi(already_awarded=already_awarded)

    report = run_award(
        api,
        operator="GitHub staging award",
        email="admin@ironhousecontracting.com",
        password="not-recorded",
    )

    assert report["status"] == "passed"
    assert report["approval_boundary"] == "staging_acceptance_award_no_external_issue"
    assert report["transition_action"] == expected_action
    assert report["project"] == {
        "id": PROJECT_ID,
        "status": "awarded",
        "job_number": JOB_NUMBER,
        "contract_value": "38080.00",
    }
    assert report["quote"]["status"] == "accepted"
    assert report["quote"]["issue_status"] == "draft"
    assert report["quote"]["job_number"] == JOB_NUMBER
    assert report["quote"]["issued_at"] is None
    assert report["idempotent_retry"] is True
    assert report["external_issuance_performed"] is False
    assert report["production_mutation_performed"] is False
    assert "not-recorded" not in str(report)

    acceptance_calls = [call for call in api.calls if call[0].endswith("/accept")]
    assert len(acceptance_calls) == 2
    assert all(call[1] == "POST" and call[2]["acceptance_reference"] == ACCEPTANCE_REFERENCE for call in acceptance_calls)
    assert not any("issue-status" in path for path, *_ in api.calls)


def test_award_fails_closed_on_quote_value_drift() -> None:
    api = FakeApi()
    api.quote["total"] = "38079.99"

    with pytest.raises(ImportValidationError, match="source mismatch"):
        run_award(
            api,
            operator="GitHub staging award",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
        )

    assert not any(path.endswith("/accept") for path, *_ in api.calls)


def test_award_fails_closed_after_external_issuance() -> None:
    api = FakeApi()
    api.quote["issued_at"] = "2026-08-28T01:00:00Z"

    with pytest.raises(ImportValidationError, match="does not cover issuance"):
        run_award(
            api,
            operator="GitHub staging award",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
        )

    assert not any(path.endswith("/accept") for path, *_ in api.calls)
