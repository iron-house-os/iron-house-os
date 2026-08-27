"""Authenticated shared-staging proof for the Bennett estimate-to-draft-quote handoff."""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from datetime import UTC, datetime
from http.cookiejar import CookieJar
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from app.core.config import get_settings
from app.services.bennett_strata_staging_import import (
    PROJECT_NAME,
    SOURCE_KEY,
    SOURCE_REVISION,
)
from app.services.drive_tender_import import ImportValidationError

EXPECTED_SUBTOTAL = "36266.67"
EXPECTED_GST = "1813.33"
EXPECTED_TOTAL = "38080.00"


class Api(Protocol):
    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any] | None: ...


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any] | None:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data is not None else {},
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                payload = response.read()
                if response.status != expected_status:
                    raise ImportValidationError(
                        f"{method} {path} returned {response.status}; expected {expected_status}."
                    )
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ImportValidationError(
                f"{method} {path} returned {error.code}; expected {expected_status}: {detail[:500]}"
            ) from error
        if not payload:
            return None
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise ImportValidationError(f"{method} {path} returned an unexpected response shape.")
        return parsed


def _one(items: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    if len(items) != 1:
        raise ImportValidationError(f"Expected exactly one {label}; found {len(items)}.")
    return items[0]


def _require_value(payload: dict[str, Any] | None, label: str) -> dict[str, Any]:
    if payload is None:
        raise ImportValidationError(f"{label} returned no JSON payload.")
    return payload


def _verify_draft_quote(quote: dict[str, Any], *, project_id: str, workspace_id: str) -> None:
    expected = {
        "project_id": project_id,
        "source_estimate_workspace_id": workspace_id,
        "customer_name": "Bennett Strata",
        "subtotal": EXPECTED_SUBTOTAL,
        "gst": EXPECTED_GST,
        "total": EXPECTED_TOTAL,
        "status": "draft",
        "issue_status": "draft",
    }
    mismatches = {
        key: {"expected": value, "actual": quote.get(key)}
        for key, value in expected.items()
        if quote.get(key) != value
    }
    if mismatches:
        raise ImportValidationError(f"Bennett draft quote mismatch: {mismatches}")
    prohibited_values = {
        "job_number": quote.get("job_number"),
        "approved_at": quote.get("approved_at"),
        "issued_at": quote.get("issued_at"),
        "accepted_at": quote.get("accepted_at"),
    }
    if any(value is not None for value in prohibited_values.values()):
        raise ImportValidationError(
            f"Bennett draft quote crossed a prohibited approval boundary: {prohibited_values}"
        )


def run_pilot(
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
    projects = _require_value(api.request("/api/v1/projects"), "Projects")
    project = _one(
        [
            item
            for item in projects.get("items", [])
            if item.get("name") == PROJECT_NAME and SOURCE_KEY in (item.get("metadata") or {})
        ],
        label="Bennett staging project",
    )
    if project.get("status") != "opportunity" or project.get("project_number") is not None:
        raise ImportValidationError(
            "Bennett staging project must remain an opportunity without a job number for this draft-only pilot."
        )
    project_id = str(project["id"])

    workspaces = _require_value(
        api.request(f"/api/v1/estimates/workspace/project/{project_id}"),
        "Estimate workspaces",
    )
    workspace = _one(
        [
            item
            for item in workspaces.get("items", [])
            if (item.get("estimate") or {}).get("source") == SOURCE_KEY
            and (item.get("estimate") or {}).get("source_revision") == SOURCE_REVISION
            and (item.get("estimate") or {}).get("estimate_key") == "concrete"
        ],
        label="authoritative Bennett concrete estimate workspace",
    )
    workspace_id = str(workspace["id"])

    quote = _require_value(
        api.request(
            f"/api/v1/customer-quotes/from-estimate/{workspace_id}",
            method="POST",
            expected_status=201,
        ),
        "Created customer quote",
    )
    _verify_draft_quote(quote, project_id=project_id, workspace_id=workspace_id)
    retry = _require_value(
        api.request(
            f"/api/v1/customer-quotes/from-estimate/{workspace_id}",
            method="POST",
            expected_status=201,
        ),
        "Retried customer quote",
    )
    _verify_draft_quote(retry, project_id=project_id, workspace_id=workspace_id)
    if retry.get("id") != quote.get("id"):
        raise ImportValidationError("Estimate-to-quote retry created a duplicate quote.")

    quotes = _require_value(api.request("/api/v1/customer-quotes"), "Customer quotes")
    linked_quotes = [
        item
        for item in quotes.get("items", [])
        if item.get("source_estimate_workspace_id") == workspace_id
    ]
    if len(linked_quotes) != 1 or linked_quotes[0].get("id") != quote.get("id"):
        raise ImportValidationError("Customer quote register does not contain one exact source-linked quote.")

    api.request("/api/v1/auth/logout", method="POST", expected_status=204)
    return {
        "status": "passed",
        "pilot": "bennett_estimate_to_draft_quote",
        "approval_boundary": "draft_only_no_award",
        "operator": operator,
        "authenticated_as": authenticated_user.get("email"),
        "authenticated_role": authenticated_user.get("role"),
        "release_id": (readiness.get("checks") or {}).get("release_id"),
        "source": SOURCE_KEY,
        "source_revision": SOURCE_REVISION,
        "project": {
            "id": project_id,
            "status": project.get("status"),
            "job_number": project.get("project_number"),
        },
        "workspace": {"id": workspace_id, "estimate_key": "concrete"},
        "quote": {
            "id": quote.get("id"),
            "quote_number": quote.get("quote_number"),
            "status": quote.get("status"),
            "issue_status": quote.get("issue_status"),
            "subtotal": quote.get("subtotal"),
            "gst": quote.get("gst"),
            "total": quote.get("total"),
            "job_number": quote.get("job_number"),
        },
        "idempotent_retry": True,
        "verified_at": datetime.now(UTC).isoformat(),
    }


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the authenticated Bennett draft-quote staging pilot.")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    if settings.environment != "staging":
        print(json.dumps({"status": "blocked", "issues": ["This pilot is staging-only."]}, indent=2))
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
