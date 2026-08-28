"""Execute and verify the explicitly approved Bennett quote award in shared staging."""

from __future__ import annotations

import json
import os
import re
from argparse import ArgumentParser
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.config import get_settings
from app.services.bennett_strata_staging_import import PROJECT_NAME, SOURCE_KEY, SOURCE_REVISION
from app.services.drive_tender_import import ImportValidationError
from app.tools.bennett_estimate_quote_staging_pilot import (
    Api,
    ApiClient,
    STAGING_BASE_URL,
    _require_value,
)

PROJECT_ID = "9ece69c0-cd6b-4d7b-b208-df77ed849e23"
WORKSPACE_ID = "6f3a07a7-6c9b-48bc-9711-0ae8230bc7b2"
QUOTE_ID = "8f854940-e710-45c2-aae4-7d5706c3a9e2"
QUOTE_NUMBER = "Q-2026-002"
EXPECTED_SUBTOTAL = "36266.67"
EXPECTED_GST = "1813.33"
EXPECTED_TOTAL = "38080.00"
ACCEPTANCE_REFERENCE = "Jeremie Peters management acceptance in ChatGPT on 2026-08-28"
ACCEPTANCE_NOTE = (
    "Accepted after Build 227 verified Bennett concrete quote Q-2026-002 in staging; "
    "staging award only."
)
JOB_NUMBER_PATTERN = re.compile(r"^IH2026\d{3}$")


def _money(value: object) -> str:
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01")))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ImportValidationError(f"Invalid money value: {value!r}") from error


def _verify_source_records(
    project: dict[str, Any],
    workspace: dict[str, Any],
    quote: dict[str, Any],
) -> None:
    project_metadata = project.get("metadata") or {}
    source_metadata = project_metadata.get(SOURCE_KEY) or {}
    estimate = workspace.get("estimate") or {}
    expected = {
        "project.id": (str(project.get("id")), PROJECT_ID),
        "project.name": (project.get("name"), PROJECT_NAME),
        "project.source_revision": (
            source_metadata.get("latest_source_revision"),
            SOURCE_REVISION,
        ),
        "workspace.id": (str(workspace.get("id")), WORKSPACE_ID),
        "workspace.source": (estimate.get("source"), SOURCE_KEY),
        "workspace.source_revision": (estimate.get("source_revision"), SOURCE_REVISION),
        "workspace.estimate_key": (estimate.get("estimate_key"), "concrete"),
        "quote.id": (str(quote.get("id")), QUOTE_ID),
        "quote.project_id": (str(quote.get("project_id")), PROJECT_ID),
        "quote.workspace_id": (
            str(quote.get("source_estimate_workspace_id")),
            WORKSPACE_ID,
        ),
        "quote.quote_number": (quote.get("quote_number"), QUOTE_NUMBER),
        "quote.customer_name": (quote.get("customer_name"), "Bennett Strata"),
        "quote.issue_status": (quote.get("issue_status"), "draft"),
        "quote.subtotal": (_money(quote.get("subtotal")), EXPECTED_SUBTOTAL),
        "quote.gst": (_money(quote.get("gst")), EXPECTED_GST),
        "quote.total": (_money(quote.get("total")), EXPECTED_TOTAL),
    }
    mismatches = {
        key: {"actual": actual, "expected": wanted}
        for key, (actual, wanted) in expected.items()
        if actual != wanted
    }
    if mismatches:
        raise ImportValidationError(f"Bennett award source mismatch: {mismatches}")
    if quote.get("issued_at") is not None:
        raise ImportValidationError("Bennett quote was externally issued; this approval does not cover issuance.")


def _classify_pre_state(project: dict[str, Any], quote: dict[str, Any]) -> str:
    project_status = project.get("status")
    project_number = project.get("project_number")
    quote_status = quote.get("status")
    quote_number = quote.get("job_number")
    if (
        project_status == "opportunity"
        and project_number is None
        and quote_status == "draft"
        and quote_number is None
        and quote.get("accepted_at") is None
    ):
        return "accept_and_award"
    if (
        project_status == "awarded"
        and isinstance(project_number, str)
        and JOB_NUMBER_PATTERN.fullmatch(project_number)
        and quote_status == "accepted"
        and quote_number == project_number
        and quote.get("accepted_at") is not None
    ):
        return "reuse_existing_award"
    raise ImportValidationError(
        "Bennett project and quote are not in the exact pre-award or idempotent awarded state."
    )


def _verify_accepted_quote(quote: dict[str, Any], *, authenticated_email: str) -> str:
    job_number = quote.get("job_number")
    expected = {
        "id": QUOTE_ID,
        "project_id": PROJECT_ID,
        "source_estimate_workspace_id": WORKSPACE_ID,
        "quote_number": QUOTE_NUMBER,
        "status": "accepted",
        "issue_status": "draft",
        "subtotal": EXPECTED_SUBTOTAL,
        "gst": EXPECTED_GST,
        "total": EXPECTED_TOTAL,
        "accepted_by": authenticated_email,
        "acceptance_reference": ACCEPTANCE_REFERENCE,
        "acceptance_note": ACCEPTANCE_NOTE,
    }
    actual = {
        **{key: quote.get(key) for key in expected},
        "id": str(quote.get("id")),
        "project_id": str(quote.get("project_id")),
        "source_estimate_workspace_id": str(quote.get("source_estimate_workspace_id")),
        "subtotal": _money(quote.get("subtotal")),
        "gst": _money(quote.get("gst")),
        "total": _money(quote.get("total")),
    }
    mismatches = {
        key: {"actual": actual.get(key), "expected": value}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if mismatches:
        raise ImportValidationError(f"Accepted Bennett quote mismatch: {mismatches}")
    if not isinstance(job_number, str) or not JOB_NUMBER_PATTERN.fullmatch(job_number):
        raise ImportValidationError(f"Invalid awarded job number: {job_number!r}")
    if quote.get("accepted_at") is None or quote.get("issued_at") is not None:
        raise ImportValidationError("Accepted quote lacks acceptance evidence or crossed issuance boundary.")
    return job_number


def _verify_awarded_project(project: dict[str, Any], *, job_number: str) -> dict[str, Any]:
    if project.get("status") != "awarded" or project.get("project_number") != job_number:
        raise ImportValidationError("Bennett project was not awarded under the quote job number.")
    if _money(project.get("contract_value")) != EXPECTED_TOTAL:
        raise ImportValidationError("Bennett awarded contract value does not match the accepted quote.")
    metadata = project.get("metadata") or {}
    baseline = metadata.get("award_pricing_baseline") or {}
    procurement = metadata.get("procurement_plan") or {}
    expected_baseline = {
        "source_quote_id": QUOTE_ID,
        "source_quote_number": QUOTE_NUMBER,
        "pricing_subtotal": EXPECTED_SUBTOTAL,
        "basis": "accepted_customer_quote_price",
        "cost_budget_status": "needs_cost_allocation",
    }
    baseline_mismatches = {
        key: {"actual": baseline.get(key), "expected": value}
        for key, value in expected_baseline.items()
        if str(baseline.get(key)) != value
    }
    if baseline_mismatches:
        raise ImportValidationError(f"Bennett award baseline mismatch: {baseline_mismatches}")
    lines = baseline.get("lines") or []
    if not lines or any(line.get("cost_budget_amount") is not None for line in lines):
        raise ImportValidationError("Award pricing was treated as a committed cost budget.")
    if (
        procurement.get("source_quote_id") != QUOTE_ID
        or procurement.get("status") != "draft"
        or procurement.get("automatic_commitment") is not False
    ):
        raise ImportValidationError("Bennett procurement draft controls were not initialized safely.")
    requirements = procurement.get("requirements") or []
    if any(item.get("po_number") is not None or item.get("approval") is not None for item in requirements):
        raise ImportValidationError("Award initialization created a prohibited procurement commitment.")
    return {
        "award_line_count": len(lines),
        "procurement_requirement_count": len(requirements),
        "cost_budget_status": baseline.get("cost_budget_status"),
        "procurement_status": procurement.get("status"),
        "automatic_commitment": procurement.get("automatic_commitment"),
    }


def run_award(
    api: Api,
    *,
    operator: str,
    email: str,
    password: str,
) -> dict[str, Any]:
    readiness = _require_value(api.request("/readiness"), "Readiness")
    api.request(
        "/api/v1/auth/login",
        method="POST",
        body={"email": email, "password": password},
    )
    authenticated = _require_value(api.request("/api/v1/auth/me"), "Authenticated user")
    authenticated_user = authenticated.get("user") or authenticated
    authenticated_email = str(authenticated_user.get("email") or "")
    if authenticated_user.get("role") not in {"admin", "operations_manager"}:
        raise ImportValidationError("Authenticated staging user lacks management award authority.")

    project = _require_value(api.request(f"/api/v1/projects/{PROJECT_ID}"), "Bennett project")
    workspaces = _require_value(
        api.request(f"/api/v1/estimates/workspace/project/{PROJECT_ID}"),
        "Bennett estimate workspaces",
    )
    workspace_matches = [
        item for item in workspaces.get("items", []) if str(item.get("id")) == WORKSPACE_ID
    ]
    if len(workspace_matches) != 1:
        raise ImportValidationError("Expected one exact Bennett concrete estimate workspace.")
    workspace = workspace_matches[0]
    quote = _require_value(api.request(f"/api/v1/customer-quotes/{QUOTE_ID}"), "Bennett quote")
    _verify_source_records(project, workspace, quote)
    transition_action = _classify_pre_state(project, quote)

    acceptance = {
        "expected_revision": int(quote.get("record_revision") or 0),
        "acceptance_reference": ACCEPTANCE_REFERENCE,
        "acceptance_note": ACCEPTANCE_NOTE,
    }
    accepted = _require_value(
        api.request(
            f"/api/v1/customer-quotes/{QUOTE_ID}/accept",
            method="POST",
            body=acceptance,
        ),
        "Accepted Bennett quote",
    )
    job_number = _verify_accepted_quote(accepted, authenticated_email=authenticated_email)
    accepted_retry = _require_value(
        api.request(
            f"/api/v1/customer-quotes/{QUOTE_ID}/accept",
            method="POST",
            body=acceptance,
        ),
        "Idempotent Bennett acceptance retry",
    )
    retry_job_number = _verify_accepted_quote(
        accepted_retry,
        authenticated_email=authenticated_email,
    )
    immutable_fields = ("id", "record_revision", "accepted_at", "accepted_by", "acceptance_reference")
    if retry_job_number != job_number or any(
        accepted_retry.get(field) != accepted.get(field) for field in immutable_fields
    ):
        raise ImportValidationError("Acceptance retry changed the awarded quote or job number.")

    project_after = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}"),
        "Awarded Bennett project",
    )
    controls = _verify_awarded_project(project_after, job_number=job_number)
    awarded_workspace = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}/workspace"),
        "Awarded Bennett workspace",
    )
    checklist = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}/start-checklist"),
        "Bennett start checklist",
    )
    dashboard = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}/launch-dashboard"),
        "Bennett launch dashboard",
    )
    if awarded_workspace.get("job_number") != job_number:
        raise ImportValidationError("Awarded project workspace does not use the permanent job number.")
    if checklist.get("total_count") != 10 or checklist.get("completed_count") != 0:
        raise ImportValidationError("Bennett start checklist was not initialized in the expected safe state.")
    expected_dashboard = {
        "job_number": job_number,
        "mobilization_status": "not_ready",
        "award_baseline_source": QUOTE_NUMBER,
        "award_pricing_subtotal": EXPECTED_SUBTOTAL,
        "award_cost_budget_status": "needs_cost_allocation",
        "procurement_plan_status": "draft",
    }
    dashboard_actual = {
        **{key: dashboard.get(key) for key in expected_dashboard},
        "award_pricing_subtotal": _money(dashboard.get("award_pricing_subtotal")),
    }
    dashboard_mismatches = {
        key: {"actual": dashboard_actual.get(key), "expected": value}
        for key, value in expected_dashboard.items()
        if dashboard_actual.get(key) != value
    }
    if dashboard_mismatches:
        raise ImportValidationError(f"Bennett launch dashboard mismatch: {dashboard_mismatches}")

    api.request("/api/v1/auth/logout", method="POST", expected_status=204)
    return {
        "status": "passed",
        "pilot": "bennett_quote_staging_award",
        "approval_boundary": "staging_acceptance_award_no_external_issue",
        "operator": operator,
        "authenticated_as": authenticated_email,
        "authenticated_role": authenticated_user.get("role"),
        "release_id": (readiness.get("checks") or {}).get("release_id"),
        "source": SOURCE_KEY,
        "source_revision": SOURCE_REVISION,
        "transition_action": transition_action,
        "project": {
            "id": PROJECT_ID,
            "status": project_after.get("status"),
            "job_number": job_number,
            "contract_value": _money(project_after.get("contract_value")),
        },
        "workspace": {"id": WORKSPACE_ID, "estimate_key": "concrete"},
        "quote": {
            "id": QUOTE_ID,
            "quote_number": QUOTE_NUMBER,
            "status": accepted.get("status"),
            "issue_status": accepted.get("issue_status"),
            "record_revision": accepted.get("record_revision"),
            "subtotal": _money(accepted.get("subtotal")),
            "gst": _money(accepted.get("gst")),
            "total": _money(accepted.get("total")),
            "job_number": job_number,
            "accepted_at": accepted.get("accepted_at"),
            "accepted_by": accepted.get("accepted_by"),
            "acceptance_reference": accepted.get("acceptance_reference"),
            "issued_at": accepted.get("issued_at"),
        },
        "award_controls": controls,
        "project_workspace_root": awarded_workspace.get("root_folder"),
        "start_checklist": {
            "status": checklist.get("status"),
            "completed_count": checklist.get("completed_count"),
            "total_count": checklist.get("total_count"),
        },
        "launch_dashboard": {
            key: dashboard.get(key)
            for key in (
                "mobilization_status",
                "award_baseline_source",
                "award_pricing_subtotal",
                "award_cost_budget_status",
                "uncoded_award_line_count",
                "procurement_requirement_count",
                "procurement_plan_status",
                "po_request_count",
            )
        },
        "idempotent_retry": True,
        "external_issuance_performed": False,
        "production_mutation_performed": False,
        "verified_at": datetime.now(UTC).isoformat(),
    }


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Execute the approved Bennett quote award in staging.")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--base-url", default=STAGING_BASE_URL)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    if settings.environment != "staging":
        print(json.dumps({"status": "blocked", "issues": ["This award is staging-only."]}, indent=2))
        raise SystemExit(2)
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not email or not password:
        print(
            json.dumps(
                {"status": "blocked", "issues": ["Staging administrator credentials are unavailable."]},
                indent=2,
            )
        )
        raise SystemExit(2)
    try:
        report = run_award(
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
