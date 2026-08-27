from copy import deepcopy
from typing import Any

import pytest

from app.services.bennett_strata_staging_import import (
    PROJECT_NAME,
    SOURCE_KEY,
    SOURCE_REVISION,
)
from app.services.drive_tender_import import ImportValidationError
from app.tools.bennett_estimate_quote_staging_pilot import run_pilot

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
WORKSPACE_ID = "22222222-2222-4222-8222-222222222222"
QUOTE_ID = "33333333-3333-4333-8333-333333333333"


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None, int]] = []
        self.project_number: str | None = None
        self.quote = {
            "id": QUOTE_ID,
            "project_id": PROJECT_ID,
            "source_estimate_workspace_id": WORKSPACE_ID,
            "quote_number": "Q-2026-001",
            "customer_name": "Bennett Strata",
            "subtotal": "36266.67",
            "gst": "1813.33",
            "total": "38080.00",
            "status": "draft",
            "issue_status": "draft",
            "job_number": None,
            "approved_at": None,
            "issued_at": None,
            "accepted_at": None,
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
            return {"checks": {"release_id": "a" * 40}}
        if path == "/api/v1/auth/login":
            return {"user": {"email": "admin@ironhousecontracting.com", "role": "admin"}}
        if path == "/api/v1/auth/me":
            return {"user": {"email": "admin@ironhousecontracting.com", "role": "admin"}}
        if path == "/api/v1/projects":
            return {
                "items": [
                    {
                        "id": PROJECT_ID,
                        "name": PROJECT_NAME,
                        "status": "opportunity",
                        "project_number": self.project_number,
                        "metadata": {SOURCE_KEY: {"latest_source_revision": SOURCE_REVISION}},
                    }
                ],
                "total": 1,
            }
        if path == f"/api/v1/estimates/workspace/project/{PROJECT_ID}":
            return {
                "items": [
                    {
                        "id": WORKSPACE_ID,
                        "estimate": {
                            "source": SOURCE_KEY,
                            "source_revision": SOURCE_REVISION,
                            "estimate_key": "concrete",
                        },
                    }
                ],
                "total": 1,
            }
        if path == f"/api/v1/customer-quotes/from-estimate/{WORKSPACE_ID}":
            return deepcopy(self.quote)
        if path == "/api/v1/customer-quotes":
            return {"items": [deepcopy(self.quote)], "total": 1}
        if path == "/api/v1/auth/logout":
            return None
        raise AssertionError(f"Unexpected request: {method} {path}")


def test_authenticated_pilot_proves_one_draft_quote_without_crossing_approval_boundary() -> None:
    api = FakeApi()

    report = run_pilot(
        api,
        operator="GitHub staging pilot",
        email="admin@ironhousecontracting.com",
        password="not-recorded",
    )

    assert report["status"] == "passed"
    assert report["approval_boundary"] == "draft_only_no_award"
    assert report["authenticated_as"] == "admin@ironhousecontracting.com"
    assert report["project"] == {
        "id": PROJECT_ID,
        "status": "opportunity",
        "job_number": None,
    }
    assert report["workspace"]["id"] == WORKSPACE_ID
    assert report["quote"] == {
        "id": QUOTE_ID,
        "quote_number": "Q-2026-001",
        "status": "draft",
        "issue_status": "draft",
        "subtotal": "36266.67",
        "gst": "1813.33",
        "total": "38080.00",
        "job_number": None,
    }
    assert report["idempotent_retry"] is True
    assert "not-recorded" not in str(report)

    conversion_calls = [
        call
        for call in api.calls
        if call[0] == f"/api/v1/customer-quotes/from-estimate/{WORKSPACE_ID}"
    ]
    assert len(conversion_calls) == 2
    assert all(call[1] == "POST" and call[3] == 201 for call in conversion_calls)
    assert not any("accept" in path or "issue-status" in path for path, *_ in api.calls)


def test_pilot_fails_before_quote_creation_if_project_has_any_job_number() -> None:
    api = FakeApi()
    api.project_number = "STAGE-BENNETT-2026"

    with pytest.raises(ImportValidationError, match="without a job number"):
        run_pilot(
            api,
            operator="GitHub staging pilot",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
        )

    assert not any("customer-quotes" in path for path, *_ in api.calls)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("total", "38079.99", "mismatch"),
        ("status", "sent", "mismatch"),
        ("accepted_at", "2026-08-27T20:00:00Z", "prohibited approval boundary"),
    ],
)
def test_pilot_fails_closed_for_wrong_money_or_state(field: str, value: object, message: str) -> None:
    api = FakeApi()
    api.quote[field] = value

    with pytest.raises(ImportValidationError, match=message):
        run_pilot(
            api,
            operator="GitHub staging pilot",
            email="admin@ironhousecontracting.com",
            password="not-recorded",
        )
