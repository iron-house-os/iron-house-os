"""Seed and verify the approved Bennett original cost budget in shared staging."""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.config import get_settings
from app.services.bennett_strata_staging_import import PROJECT_NAME, SOURCE_KEY, SOURCE_REVISION
from app.services.drive_tender_import import ImportValidationError
from app.tools.bennett_estimate_quote_staging_pilot import Api, ApiClient, STAGING_BASE_URL, _require_value
from app.tools.bennett_quote_staging_award import PROJECT_ID, QUOTE_ID, QUOTE_NUMBER, WORKSPACE_ID

JOB_NUMBER = "IH2026002"
EXPECTED_CONTRACT_VALUE = "38080.00"
EXPECTED_CUSTOMER_SUBTOTAL = "36266.67"
EXPECTED_BUDGET = "26660.93"
EXPECTED_CODES = {
    "4100": {"name": "Concrete restoration", "budget": "24610.93"},
    "5100": {"name": "Small equipment rental", "budget": "200.00"},
    "5110": {"name": "Skid steer / hydraulic attachment", "budget": "1100.00"},
    "6100": {"name": "Trucking, disposal and material hauling", "budget": "750.00"},
}
BUDGET_REQUEST = {
    "workspace_id": WORKSPACE_ID,
    "cost_code_mappings": {
        "CON-001": "4100",
        "EQP-001": "5100",
        "EQP-002": "5110",
        "TRK-001": "6100",
    },
    "cost_code_names": {code: values["name"] for code, values in EXPECTED_CODES.items()},
    "risk_cost_code": "4100",
    "risk_cost_code_name": "Concrete restoration",
}


def _money(value: object) -> str:
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01")))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ImportValidationError(f"Invalid money value: {value!r}") from error


def _budget_entries(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in summary.get("entries", []) if item.get("entry_type") == "budget"]


def _verify_financial_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {
        "project_id": PROJECT_ID,
        "contract_value": EXPECTED_CONTRACT_VALUE,
        "budget": EXPECTED_BUDGET,
        "committed": "0.00",
        "actual": "0.00",
        "forecast_cost": "0.00",
    }
    actual = {
        "project_id": str(summary.get("project_id")),
        **{key: _money(summary.get(key)) for key in expected if key != "project_id"},
    }
    mismatches = {
        key: {"actual": actual.get(key), "expected": value}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if mismatches:
        raise ImportValidationError(f"Bennett financial summary mismatch: {mismatches}")
    entries = _budget_entries(summary)
    if len(entries) != 5 or len(summary.get("entries", [])) != 5:
        raise ImportValidationError("Bennett financial summary must contain only five budget entries.")
    if any(
        item.get("source_type") != "estimate_workspace"
        or str(item.get("source_id")) != WORKSPACE_ID
        or not item.get("source_key")
        or item.get("status") != "posted"
        for item in entries
    ):
        raise ImportValidationError("Bennett budget entries lack immutable estimate provenance.")
    code_totals: dict[str, Decimal] = {}
    for item in entries:
        code = str(item.get("cost_code") or "")
        code_totals[code] = code_totals.get(code, Decimal("0")) + Decimal(str(item.get("amount")))
    normalized = {code: str(value.quantize(Decimal("0.01"))) for code, value in code_totals.items()}
    wanted = {code: values["budget"] for code, values in EXPECTED_CODES.items()}
    if normalized != wanted:
        raise ImportValidationError(f"Bennett cost-code totals mismatch: {normalized}")
    return entries


def _verify_exact_source(
    project: dict[str, Any],
    workspace: dict[str, Any],
    quote: dict[str, Any],
) -> None:
    bid_json = workspace.get("estimate") or {}
    summary = bid_json.get("summary") or {}
    source_metadata = (project.get("metadata") or {}).get(SOURCE_KEY) or {}
    expected = {
        "project.id": (str(project.get("id")), PROJECT_ID),
        "project.name": (project.get("name"), PROJECT_NAME),
        "project.status": (project.get("status"), "awarded"),
        "project.job_number": (project.get("project_number"), JOB_NUMBER),
        "project.contract_value": (_money(project.get("contract_value")), EXPECTED_CONTRACT_VALUE),
        "project.source_revision": (source_metadata.get("latest_source_revision"), SOURCE_REVISION),
        "workspace.id": (str(workspace.get("id")), WORKSPACE_ID),
        "workspace.source": (bid_json.get("source"), SOURCE_KEY),
        "workspace.source_revision": (bid_json.get("source_revision"), SOURCE_REVISION),
        "workspace.estimate_key": (bid_json.get("estimate_key"), "concrete"),
        "workspace.direct_cost": (_money(summary.get("direct_cost")), "21910.93"),
        "workspace.risk_cost": (_money(summary.get("risk_cost")), "4750.00"),
        "workspace.cost_basis": (
            _money(Decimal(str(summary.get("direct_cost"))) + Decimal(str(summary.get("risk_cost")))),
            EXPECTED_BUDGET,
        ),
        "quote.id": (str(quote.get("id")), QUOTE_ID),
        "quote.quote_number": (quote.get("quote_number"), QUOTE_NUMBER),
        "quote.status": (quote.get("status"), "accepted"),
        "quote.issue_status": (quote.get("issue_status"), "draft"),
        "quote.job_number": (quote.get("job_number"), JOB_NUMBER),
        "quote.subtotal": (_money(quote.get("subtotal")), EXPECTED_CUSTOMER_SUBTOTAL),
        "quote.total": (_money(quote.get("total")), EXPECTED_CONTRACT_VALUE),
    }
    mismatches = {
        key: {"actual": actual, "expected": wanted}
        for key, (actual, wanted) in expected.items()
        if actual != wanted
    }
    if mismatches:
        raise ImportValidationError(f"Bennett budget source mismatch: {mismatches}")
    if quote.get("issued_at") is not None:
        raise ImportValidationError("Bennett quote issuance is outside this budget approval.")


def _verify_project_controls(project: dict[str, Any]) -> list[dict[str, str]]:
    metadata = project.get("metadata") or {}
    baseline = metadata.get("award_pricing_baseline") or {}
    procurement = metadata.get("procurement_plan") or {}
    if baseline.get("pricing_subtotal") != EXPECTED_CUSTOMER_SUBTOTAL:
        raise ImportValidationError("Customer pricing baseline changed during cost-budget allocation.")
    if (
        baseline.get("cost_budget_status") != "allocated"
        or str(baseline.get("cost_budget_source_workspace_id")) != WORKSPACE_ID
        or _money(baseline.get("cost_budget_total")) != EXPECTED_BUDGET
    ):
        raise ImportValidationError("Bennett award cost-budget metadata was not allocated exactly.")
    lines = baseline.get("cost_budget_lines") or []
    if len(lines) != 5 or any(not line.get("cost_code") for line in lines):
        raise ImportValidationError("Bennett cost-budget detail is missing or uncoded.")
    if (
        procurement.get("status") != "draft"
        or procurement.get("automatic_commitment") is not False
        or any(
            item.get("po_number") is not None or item.get("approval") is not None
            for item in procurement.get("requirements") or []
        )
    ):
        raise ImportValidationError("Cost-budget allocation crossed the procurement boundary.")
    codes = metadata.get("project_cost_codes") or []
    normalized = [{"code": item.get("code"), "name": item.get("name")} for item in codes]
    wanted = [{"code": code, "name": values["name"]} for code, values in EXPECTED_CODES.items()]
    if normalized != wanted:
        raise ImportValidationError(f"Bennett project cost-code directory mismatch: {normalized}")
    return normalized


def run_pilot(api: Api, *, operator: str, email: str, password: str) -> dict[str, Any]:
    readiness = _require_value(api.request("/readiness"), "Readiness")
    api.request("/api/v1/auth/login", method="POST", body={"email": email, "password": password})
    authenticated = _require_value(api.request("/api/v1/auth/me"), "Authenticated user")
    authenticated_user = authenticated.get("user") or authenticated
    if authenticated_user.get("role") not in {"admin", "operations_manager"}:
        raise ImportValidationError("Authenticated staging user lacks management financial access.")

    project = _require_value(api.request(f"/api/v1/projects/{PROJECT_ID}"), "Bennett project")
    quote = _require_value(api.request(f"/api/v1/customer-quotes/{QUOTE_ID}"), "Bennett quote")
    workspaces = _require_value(
        api.request(f"/api/v1/estimates/workspace/project/{PROJECT_ID}"),
        "Bennett workspaces",
    )
    matches = [item for item in workspaces.get("items", []) if str(item.get("id")) == WORKSPACE_ID]
    if len(matches) != 1:
        raise ImportValidationError("Expected one exact Bennett concrete estimate workspace.")
    workspace = matches[0]
    _verify_exact_source(project, workspace, quote)

    before = _require_value(
        api.request(f"/api/v1/finance/projects/{PROJECT_ID}"),
        "Bennett financial baseline",
    )
    before_budget = _money(before.get("budget"))
    if before_budget == "0.00" and not before.get("entries"):
        transition_action = "create_original_cost_budget"
    elif before_budget == EXPECTED_BUDGET:
        _verify_financial_summary(before)
        transition_action = "reuse_existing_cost_budget"
    else:
        raise ImportValidationError("Bennett already has an unexpected financial baseline.")
    if any(_money(before.get(key)) != "0.00" for key in ("committed", "actual", "forecast_cost")):
        raise ImportValidationError("Bennett has commitments or actuals outside this budget-only approval.")

    imported = _require_value(
        api.request(
            f"/api/v1/finance/projects/{PROJECT_ID}/import-estimate",
            method="POST",
            body=BUDGET_REQUEST,
        ),
        "Imported Bennett cost budget",
    )
    first_entries = _verify_financial_summary(imported)
    retry = _require_value(
        api.request(
            f"/api/v1/finance/projects/{PROJECT_ID}/import-estimate",
            method="POST",
            body=BUDGET_REQUEST,
        ),
        "Retried Bennett cost budget",
    )
    retry_entries = _verify_financial_summary(retry)
    def identity(items: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
        return sorted(
            (str(item.get("id")), str(item.get("source_key")), _money(item.get("amount")))
            for item in items
        )

    if identity(first_entries) != identity(retry_entries):
        raise ImportValidationError("Bennett cost-budget retry changed entry identity or value.")

    project_after = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}"),
        "Bennett project after budget import",
    )
    project_codes = _verify_project_controls(project_after)
    dashboard = _require_value(
        api.request(f"/api/v1/projects/{PROJECT_ID}/launch-dashboard"),
        "Bennett launch dashboard",
    )
    dashboard_expected = {
        "job_number": JOB_NUMBER,
        "mobilization_status": "not_ready",
        "baseline_budget_total": EXPECTED_BUDGET,
        "budget_entry_count": 5,
        "award_baseline_source": QUOTE_NUMBER,
        "award_pricing_subtotal": EXPECTED_CUSTOMER_SUBTOTAL,
        "award_cost_budget_status": "allocated",
        "uncoded_award_line_count": 0,
        "procurement_plan_status": "draft",
        "po_request_count": 0,
    }
    dashboard_actual = {
        **{key: dashboard.get(key) for key in dashboard_expected},
        "baseline_budget_total": _money(dashboard.get("baseline_budget_total")),
        "award_pricing_subtotal": _money(dashboard.get("award_pricing_subtotal")),
    }
    dashboard_mismatches = {
        key: {"actual": dashboard_actual.get(key), "expected": value}
        for key, value in dashboard_expected.items()
        if dashboard_actual.get(key) != value
    }
    if dashboard_mismatches:
        raise ImportValidationError(f"Bennett launch dashboard mismatch: {dashboard_mismatches}")
    timesheets = _require_value(
        api.request("/api/v1/daily-timesheets/bootstrap"),
        "Daily timesheet bootstrap",
    )
    if (timesheets.get("project_cost_codes") or {}).get(PROJECT_ID) != project_codes:
        raise ImportValidationError("Bennett approved job cost codes are unavailable to daily timesheets.")

    api.request("/api/v1/auth/logout", method="POST", expected_status=204)
    return {
        "status": "passed",
        "pilot": "bennett_original_cost_budget",
        "approval_boundary": "staging_original_budget_only_no_commitments",
        "operator": operator,
        "authenticated_as": authenticated_user.get("email"),
        "authenticated_role": authenticated_user.get("role"),
        "release_id": (readiness.get("checks") or {}).get("release_id"),
        "source": SOURCE_KEY,
        "source_revision": SOURCE_REVISION,
        "transition_action": transition_action,
        "project": {"id": PROJECT_ID, "job_number": JOB_NUMBER, "status": "awarded"},
        "quote": {
            "id": QUOTE_ID,
            "quote_number": QUOTE_NUMBER,
            "status": quote.get("status"),
            "subtotal": _money(quote.get("subtotal")),
            "total": _money(quote.get("total")),
            "issued_at": quote.get("issued_at"),
        },
        "workspace": {"id": WORKSPACE_ID, "estimate_key": "concrete"},
        "budget": {
            "total": EXPECTED_BUDGET,
            "entry_count": len(first_entries),
            "cost_codes": EXPECTED_CODES,
            "status": "allocated",
        },
        "project_cost_codes": project_codes,
        "idempotent_retry": True,
        "commitments_created": 0,
        "actuals_created": 0,
        "po_requests_created": 0,
        "checklist_items_completed": 0,
        "external_issuance_performed": False,
        "production_mutation_performed": False,
        "verified_at": datetime.now(UTC).isoformat(),
    }


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Seed the approved Bennett original cost budget in staging.")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--base-url", default=STAGING_BASE_URL)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    if settings.environment != "staging":
        print(json.dumps({"status": "blocked", "issues": ["This budget pilot is staging-only."]}, indent=2))
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
