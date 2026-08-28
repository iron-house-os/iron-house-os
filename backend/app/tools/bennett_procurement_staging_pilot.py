"""Seed and verify the approved Bennett procurement planning requirements in staging."""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.services.bennett_strata_staging_import import SOURCE_KEY, SOURCE_REVISION
from app.services.drive_tender_import import ImportValidationError
from app.tools.bennett_cost_budget_staging_pilot import (
    BUDGET_REQUEST,
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

PROCUREMENT_REQUIREMENTS = [
    {
        "source_code": "CON-001",
        "category": "material",
        "description": "Ready-mix concrete planning requirement",
        "order_quantity": None,
        "order_unit": "m3",
        "order_quantity_status": "needs_confirmation",
        "specification": (
            "4 in concrete scope; mix, order quantity, delivery and placement details "
            "require confirmation."
        ),
    },
    {
        "source_code": "EQP-001",
        "category": "rental",
        "description": "14 in cutoff saw including blade wear and consumables",
        "order_quantity": "1",
        "order_unit": "day",
        "order_quantity_status": "planning_basis",
    },
    {
        "source_code": "EQP-002",
        "category": "rental",
        "description": "Skid steer with hydraulic hammer",
        "order_quantity": "1",
        "order_unit": "day",
        "order_quantity_status": "planning_basis",
    },
    {
        "source_code": "TRK-001",
        "category": "trucking",
        "description": "Tandem allowance for concrete disposal",
        "order_quantity": "1",
        "order_unit": "LS",
        "order_quantity_status": "planning_basis",
    },
]
PROCUREMENT_REQUEST = {
    **BUDGET_REQUEST,
    "procurement_requirements": PROCUREMENT_REQUIREMENTS,
}
EXPECTED_REQUIREMENTS = [
    {
        "source_code": "CON-001",
        "cost_code": "4100",
        "category": "material",
        "description": "Ready-mix concrete planning requirement",
        "scope_quantity": "108.6",
        "scope_unit": "m2",
        "order_quantity": None,
        "order_unit": "m3",
        "order_quantity_status": "needs_confirmation",
        "budget_basis": "19860.93",
        "budget_basis_type": "source_estimate_line_cost_not_authorized_spend",
        "status": "needs_quantity_confirmation",
        "specification": (
            "4 in concrete scope; mix, order quantity, delivery and placement details "
            "require confirmation."
        ),
    },
    {
        "source_code": "EQP-001",
        "cost_code": "5100",
        "category": "rental",
        "description": "14 in cutoff saw including blade wear and consumables",
        "scope_quantity": "1.0",
        "scope_unit": "day",
        "order_quantity": "1",
        "order_unit": "day",
        "order_quantity_status": "planning_basis",
        "budget_basis": "200.00",
        "budget_basis_type": "source_estimate_line_cost_not_authorized_spend",
        "status": "not_started",
        "specification": None,
    },
    {
        "source_code": "EQP-002",
        "cost_code": "5110",
        "category": "rental",
        "description": "Skid steer with hydraulic hammer",
        "scope_quantity": "1.0",
        "scope_unit": "day",
        "order_quantity": "1",
        "order_unit": "day",
        "order_quantity_status": "planning_basis",
        "budget_basis": "1100.00",
        "budget_basis_type": "source_estimate_line_cost_not_authorized_spend",
        "status": "not_started",
        "specification": None,
    },
    {
        "source_code": "TRK-001",
        "cost_code": "6100",
        "category": "trucking",
        "description": "Tandem allowance for concrete disposal",
        "scope_quantity": "1.0",
        "scope_unit": "LS",
        "order_quantity": "1",
        "order_unit": "LS",
        "order_quantity_status": "planning_basis",
        "budget_basis": "750.00",
        "budget_basis_type": "source_estimate_line_cost_not_authorized_spend",
        "status": "not_started",
        "specification": None,
    },
]


def _safe_draft_plan(project: dict[str, Any]) -> dict[str, Any]:
    plan = (project.get("metadata") or {}).get("procurement_plan") or {}
    if plan.get("status") != "draft" or plan.get("automatic_commitment") is not False:
        raise ImportValidationError("Bennett procurement baseline is not a safe draft plan.")
    protected = (
        "vendor_id",
        "vendor_quote_reference",
        "required_on_site_date",
        "approval",
        "po_number",
    )
    if any(
        item.get("status") not in {None, "not_started", "needs_quantity_confirmation"}
        or item.get("commitment_created") is True
        or any(item.get(field) is not None for field in protected)
        for item in plan.get("requirements") or []
    ):
        raise ImportValidationError("Bennett procurement baseline contains a decision or commitment.")
    return plan


def _verify_procurement_plan(project: dict[str, Any]) -> list[dict[str, Any]]:
    plan = _safe_draft_plan(project)
    expected_plan = {
        "source_quote_id": QUOTE_ID,
        "source_estimate_workspace_id": WORKSPACE_ID,
        "job_number": JOB_NUMBER,
        "status": "draft",
        "automatic_commitment": False,
    }
    mismatches = {
        key: {"actual": plan.get(key), "expected": value}
        for key, value in expected_plan.items()
        if plan.get(key) != value
    }
    if mismatches:
        raise ImportValidationError(f"Bennett procurement plan mismatch: {mismatches}")
    requirements = plan.get("requirements") or []
    if len(requirements) != len(EXPECTED_REQUIREMENTS):
        raise ImportValidationError("Bennett procurement plan must contain four requirements.")
    actual = [
        {key: item.get(key) for key in expected}
        for item, expected in zip(requirements, EXPECTED_REQUIREMENTS, strict=True)
    ]
    if actual != EXPECTED_REQUIREMENTS:
        raise ImportValidationError(f"Bennett procurement requirements mismatch: {actual}")
    if len({item.get("requirement_id") for item in requirements}) != 4:
        raise ImportValidationError("Bennett procurement requirement identities are not unique.")
    if any(
        item.get("source_type") != "estimate_workspace"
        or str(item.get("source_estimate_workspace_id")) != WORKSPACE_ID
        or not str(item.get("source_budget_key") or "").startswith(
            f"estimate-budget:{WORKSPACE_ID}:"
        )
        or item.get("job_number") != JOB_NUMBER
        or item.get("commitment_created") is not False
        for item in requirements
    ):
        raise ImportValidationError("Bennett procurement requirements lack exact job/budget provenance.")
    if any(item.get("source_code") == "RISK" for item in requirements):
        raise ImportValidationError("The Bennett risk allowance became a procurement requirement.")
    return requirements


def _require_safe_dashboard(api: Api) -> dict[str, Any]:
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
        "award_cost_budget_status": "allocated",
        "uncoded_award_line_count": 0,
        "procurement_plan_status": "draft",
        "po_request_count": 0,
        "pending_po_request_count": 0,
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
        raise ImportValidationError(f"Bennett launch control mismatch: {mismatches}")
    return dashboard


def run_pilot(api: Api, *, operator: str, email: str, password: str) -> dict[str, Any]:
    readiness = _require_value(api.request("/readiness"), "Readiness")
    api.request("/api/v1/auth/login", method="POST", body={"email": email, "password": password})
    authenticated = _require_value(api.request("/api/v1/auth/me"), "Authenticated user")
    authenticated_user = authenticated.get("user") or authenticated
    if authenticated_user.get("role") not in {"admin", "operations_manager"}:
        raise ImportValidationError("Authenticated staging user lacks procurement planning access.")

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
    _safe_draft_plan(project)
    before = _require_value(
        api.request(f"/api/v1/finance/projects/{PROJECT_ID}"),
        "Bennett financial baseline",
    )
    _verify_financial_summary(before)
    before_dashboard = _require_safe_dashboard(api)
    if before_dashboard.get("procurement_requirement_count") == 4:
        _verify_procurement_plan(project)
        transition_action = "reuse_existing_procurement_plan"
    elif before_dashboard.get("procurement_requirement_count") == 1:
        transition_action = "replace_safe_quote_procurement_shell"
    else:
        raise ImportValidationError("Bennett has an unexpected procurement requirement count.")

    first = _require_value(
        api.request(
            f"/api/v1/finance/projects/{PROJECT_ID}/import-estimate",
            method="POST",
            body=PROCUREMENT_REQUEST,
        ),
        "Generated Bennett procurement plan",
    )
    first_entries = _verify_financial_summary(first)
    first_project = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}"),
        "Bennett project after procurement generation",
    )
    first_requirements = _verify_procurement_plan(first_project)
    retry = _require_value(
        api.request(
            f"/api/v1/finance/projects/{PROJECT_ID}/import-estimate",
            method="POST",
            body=PROCUREMENT_REQUEST,
        ),
        "Retried Bennett procurement plan",
    )
    retry_entries = _verify_financial_summary(retry)
    retry_project = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}"),
        "Bennett project after procurement retry",
    )
    retry_requirements = _verify_procurement_plan(retry_project)

    def entry_identity(items: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
        return sorted(
            (str(item.get("id")), str(item.get("source_key")), _money(item.get("amount")))
            for item in items
        )

    def requirement_identity(items: list[dict[str, Any]]) -> list[tuple[str, str]]:
        return sorted(
            (str(item.get("requirement_id")), str(item.get("source_budget_key")))
            for item in items
        )

    if entry_identity(first_entries) != entry_identity(retry_entries):
        raise ImportValidationError("Procurement generation changed original budget-entry identity.")
    if requirement_identity(first_requirements) != requirement_identity(retry_requirements):
        raise ImportValidationError("Bennett procurement retry changed requirement identity.")
    dashboard = _require_safe_dashboard(api)
    if dashboard.get("procurement_requirement_count") != 4:
        raise ImportValidationError("Bennett launch dashboard lacks four procurement requirements.")

    api.request("/api/v1/auth/logout", method="POST", expected_status=204)
    return {
        "status": "passed",
        "pilot": "bennett_procurement_planning",
        "approval_boundary": "staging_procurement_planning_only_no_commitments",
        "operator": operator,
        "authenticated_as": authenticated_user.get("email"),
        "authenticated_role": authenticated_user.get("role"),
        "release_id": (readiness.get("checks") or {}).get("release_id"),
        "source": SOURCE_KEY,
        "source_revision": SOURCE_REVISION,
        "transition_action": transition_action,
        "project": {"id": PROJECT_ID, "job_number": JOB_NUMBER, "status": "awarded"},
        "workspace": {"id": WORKSPACE_ID, "estimate_key": "concrete"},
        "budget": {"total": EXPECTED_BUDGET, "entry_count": len(first_entries)},
        "procurement": {
            "status": "draft",
            "requirement_count": len(first_requirements),
            "requirements": EXPECTED_REQUIREMENTS,
            "ready_mix_order_quantity_confirmed": False,
        },
        "idempotent_retry": True,
        "vendors_selected": 0,
        "commitments_created": 0,
        "po_requests_created": 0,
        "actuals_created": 0,
        "checklist_items_completed": 0,
        "external_issuance_performed": False,
        "production_mutation_performed": False,
        "verified_at": datetime.now(UTC).isoformat(),
    }


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Seed the approved Bennett procurement plan in staging.")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--base-url", default=STAGING_BASE_URL)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    if settings.environment != "staging":
        print(json.dumps({"status": "blocked", "issues": ["This procurement pilot is staging-only."]}, indent=2))
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
