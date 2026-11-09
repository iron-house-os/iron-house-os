#!/usr/bin/env python3
"""Validate and import approval-gated IHOS business-record bundles.

Only stdlib modules are used so the same trusted script can run on the
restricted production runner. All imported quotes and invoices remain drafts.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


MONEY = Decimal("0.01")
IMPORT_MARKER = "IHOS_IMPORT_REF"


def money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def quote_totals(payload: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum(
        money(Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"])))
        for item in payload["line_items"]
    )
    subtotal = money(subtotal)
    gst = money(subtotal * Decimal(str(payload.get("gst_rate", "5.00"))) / Decimal("100"))
    return subtotal, gst, money(subtotal + gst)


def invoice_totals(payload: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum(
        money(Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"])))
        for item in payload["line_items"]
    )
    subtotal = money(subtotal)
    gst = money(subtotal * Decimal(str(payload.get("gst_rate", "5.00"))) / Decimal("100"))
    return subtotal, gst, money(subtotal + gst)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_expected(record: dict[str, Any], calculated: tuple[Decimal, Decimal, Decimal], label: str) -> None:
    expected = tuple(money(record[key]) for key in ("expected_subtotal", "expected_gst", "expected_total"))
    _require(calculated == expected, f"{label} totals mismatch: calculated={calculated}, expected={expected}")


def _validate_selection_options(record: dict[str, Any], label: str) -> None:
    if not record.get("selection_required"):
        _require(not record.get("selection_options"), f"{label} selection_options require selection_required")
        return

    options = record.get("selection_options") or []
    _require(len(options) == 3, f"{label} must contain exactly three mutually exclusive options")
    names = [option.get("name") for option in options]
    _require(all(names) and len(set(names)) == len(names), f"{label} option names must be present and unique")
    for option in options:
        subtotal = money(option["subtotal"])
        gst = money(option["gst"])
        total = money(option["total"])
        _require(subtotal > 0, f"{label} {option['name']} subtotal must be positive")
        _require(gst == money(subtotal * Decimal("0.05")), f"{label} {option['name']} GST must be 5%")
        _require(total == money(subtotal + gst), f"{label} {option['name']} total must equal subtotal plus GST")

    expected = tuple(money(record[key]) for key in ("expected_subtotal", "expected_gst", "expected_total"))
    _require(expected == (Decimal("0.00"),) * 3, f"{label} calculated draft totals must remain zero until selection")
    notes = (record.get("payload") or {}).get("notes") or ""
    _require("must not be added together" in notes, f"{label} notes must prohibit adding mutually exclusive options")


def validate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    _require(bundle.get("schema_version") == 1, "schema_version must be 1")
    _require(isinstance(bundle.get("issue_number"), int) and bundle["issue_number"] > 0, "issue_number is required")
    _require(bool(bundle.get("import_key")), "import_key is required")

    project = bundle.get("project") or {}
    project_payload = project.get("payload") or {}
    _require(project.get("import_key") == bundle["import_key"], "project import_key must match bundle import_key")
    _require(project_payload.get("status") == "opportunity", "intake projects must remain opportunities")
    _require(not project_payload.get("project_number"), "intake must not allocate a project/job number")
    _require(project_payload.get("name") and project_payload.get("client_owner"), "project name and client_owner are required")
    _require(project_payload.get("project_address"), "project_address is required")
    metadata = project_payload.get("metadata") or {}
    _require(metadata.get("source_import_key") == bundle["import_key"], "project metadata must carry source_import_key")

    seen: set[str] = set()
    quotes = bundle.get("quotes") or []
    _require(len(quotes) == 3, "this intake bundle must contain exactly three draft quotes")
    for record in quotes:
        ref = record.get("external_reference")
        _require(bool(ref) and ref not in seen, "quote external references must be present and unique")
        seen.add(ref)
        payload = record.get("payload") or {}
        _require("status" not in payload and "issue_status" not in payload, f"{ref} must use API draft defaults")
        _require(payload.get("project_name") and payload.get("customer_name"), f"{ref} is missing customer/project data")
        _require(payload.get("scope_summary") and payload.get("line_items"), f"{ref} is missing scope or line items")
        _require(payload.get("quote_date"), f"{ref} quote_date is required before import")
        _require(payload.get("valid_until"), f"{ref} valid_until is required before import")
        _require(payload.get("gst_rate") is not None, f"{ref} gst_rate is required before import")
        _require(all(Decimal(str(item["quantity"])) > 0 for item in payload["line_items"]), f"{ref} quantities must be positive")
        marker = f"[{IMPORT_MARKER}:{ref}]"
        _require(marker in (payload.get("notes") or ""), f"{ref} notes must contain {marker}")
        _validate_expected(record, quote_totals(payload), ref)
        _validate_selection_options(record, ref)

    invoices = bundle.get("invoices") or []
    _require(len(invoices) == 1, "this intake bundle must contain exactly one draft invoice")
    for record in invoices:
        ref = record.get("external_reference")
        _require(bool(ref) and ref not in seen, "invoice external references must be present and unique")
        seen.add(ref)
        payload = record.get("payload") or {}
        _require("status" not in payload, f"{ref} must use the API draft default")
        _require(payload.get("invoice_number") == ref, f"{ref} must match invoice_number")
        _require(payload.get("customer_name") and payload.get("customer_address"), f"{ref} client billing data is required")
        _require(payload.get("line_items"), f"{ref} line items are required")
        _require(payload.get("project_name") and payload.get("site_address"), f"{ref} project/site data is required")
        _require(payload.get("invoice_date") and payload.get("due_date"), f"{ref} invoice and due dates are required")
        _require(payload.get("terms") and payload.get("gst_rate") is not None, f"{ref} terms and gst_rate are required")
        _validate_expected(record, invoice_totals(payload), ref)

    return {
        "import_key": bundle["import_key"],
        "issue_number": bundle["issue_number"],
        "project_count": 1,
        "quote_count": len(quotes),
        "invoice_count": len(invoices),
        "validated": True,
    }


class IHOSClient:
    def __init__(self) -> None:
        port = os.environ.get("IHOS_PORT", "8080")
        self.base = f"http://127.0.0.1:{port}"
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(self, path: str, method: str = "GET", body: dict[str, Any] | None = None, expected: tuple[int, ...] = (200,)) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                result = json.load(response)
                if response.status not in expected:
                    raise RuntimeError(f"Unexpected status {response.status}")
                return result
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"IHOS request failed: {exc.code} {detail}") from exc

    def login(self) -> None:
        result = self.request(
            "/api/v1/auth/login",
            method="POST",
            body={
                "email": os.environ["BOOTSTRAP_ADMIN_EMAIL"],
                "password": os.environ["BOOTSTRAP_ADMIN_PASSWORD"],
            },
        )
        if result.get("authentication") != "authenticated":
            raise RuntimeError("IHOS login did not authenticate")


def _marker(ref: str) -> str:
    return f"[{IMPORT_MARKER}:{ref}]"


def _assert_equal(actual: Any, expected: Any, label: str) -> None:
    if str(actual) != str(expected):
        raise RuntimeError(f"Verification failed for {label}: {actual!r} != {expected!r}")


def _verify_project(project: dict[str, Any], expected: dict[str, Any], import_key: str) -> None:
    for field in ("name", "client_owner", "project_address", "status"):
        _assert_equal(project.get(field), expected.get(field), f"project.{field}")
    _assert_equal((project.get("metadata") or {}).get("source_import_key"), import_key, "project.metadata.source_import_key")
    if project.get("project_number"):
        raise RuntimeError("Opportunity import unexpectedly has a project/job number")


def _verify_quote(quote: dict[str, Any], record: dict[str, Any], project_id: str) -> None:
    payload = record["payload"]
    for field in ("customer_name", "customer_email", "customer_phone", "site_address", "quote_date"):
        _assert_equal(quote.get(field), payload.get(field), f"{record['external_reference']}.{field}")
    _assert_equal(quote.get("project_id"), project_id, f"{record['external_reference']}.project_id")
    _assert_equal(quote.get("subtotal"), record["expected_subtotal"], f"{record['external_reference']}.subtotal")
    _assert_equal(quote.get("gst"), record["expected_gst"], f"{record['external_reference']}.gst")
    _assert_equal(quote.get("total"), record["expected_total"], f"{record['external_reference']}.total")
    _assert_equal(quote.get("status"), "draft", f"{record['external_reference']}.status")
    _assert_equal(quote.get("issue_status"), "draft", f"{record['external_reference']}.issue_status")


def _verify_invoice(invoice: dict[str, Any], record: dict[str, Any]) -> None:
    payload = record["payload"]
    for field in ("invoice_number", "project_name", "site_address", "customer_name", "customer_address", "customer_phone", "invoice_date", "due_date", "terms"):
        _assert_equal(invoice.get(field), payload.get(field), f"{record['external_reference']}.{field}")
    _assert_equal(invoice.get("subtotal"), record["expected_subtotal"], f"{record['external_reference']}.subtotal")
    _assert_equal(invoice.get("gst"), record["expected_gst"], f"{record['external_reference']}.gst")
    _assert_equal(invoice.get("total"), record["expected_total"], f"{record['external_reference']}.total")
    _assert_equal(invoice.get("status"), "draft", f"{record['external_reference']}.status")


def import_bundle(bundle: dict[str, Any], client: IHOSClient) -> dict[str, Any]:
    validation = validate_bundle(bundle)
    client.login()

    project_record = bundle["project"]
    project_payload = project_record["payload"]
    projects = client.request("/api/v1/projects").get("items", [])
    matches = [
        item for item in projects
        if (item.get("metadata") or {}).get("source_import_key") == bundle["import_key"]
    ]
    if len(matches) > 1:
        raise RuntimeError("Multiple projects match the source import key")
    if matches:
        project = matches[0]
        project_operation = "verified_existing"
    else:
        conflicting = [
            item for item in projects
            if item.get("name") == project_payload["name"]
            and item.get("project_address") == project_payload["project_address"]
        ]
        if conflicting:
            raise RuntimeError("A same-name/same-address project exists without the import key; manual review required")
        project = client.request("/api/v1/projects", method="POST", body=project_payload, expected=(201,))
        project_operation = "created"
    _verify_project(project, project_payload, bundle["import_key"])

    quote_listing = client.request("/api/v1/customer-quotes").get("items", [])
    quote_evidence = []
    for record in bundle["quotes"]:
        ref = record["external_reference"]
        matches = [item for item in quote_listing if _marker(ref) in (item.get("notes") or "")]
        if len(matches) > 1:
            raise RuntimeError(f"Multiple customer quotes match {ref}")
        if matches:
            quote = matches[0]
            operation = "verified_existing"
        else:
            payload = dict(record["payload"])
            payload["project_id"] = project["id"]
            quote = client.request("/api/v1/customer-quotes", method="POST", body=payload, expected=(201,))
            quote_listing.append(quote)
            operation = "created"
        _verify_quote(quote, record, project["id"])
        quote_evidence.append({
            "external_reference": ref,
            "ihos_quote_number": quote["quote_number"],
            "id": quote["id"],
            "operation": operation,
            "status": quote["status"],
            "issue_status": quote["issue_status"],
            "total": quote["total"],
        })

    refreshed_projects = client.request("/api/v1/projects").get("items", [])
    invoice_listing = client.request("/api/v1/finance/customer-invoices").get("items", [])
    invoice_evidence = []
    for record in bundle["invoices"]:
        ref = record["external_reference"]
        matches = [item for item in invoice_listing if item.get("invoice_number") == ref]
        if len(matches) > 1:
            raise RuntimeError(f"Multiple customer invoices match {ref}")
        if matches:
            invoice = matches[0]
            operation = "verified_existing"
        else:
            payload = dict(record["payload"])
            project_match = record.get("project_match") or {}
            source_quote_number = project_match.get("source_quote_number")
            if source_quote_number:
                linked = [
                    item for item in refreshed_projects
                    if (item.get("metadata") or {}).get("source_quote_number") == source_quote_number
                ]
                if len(linked) > 1:
                    raise RuntimeError(f"Multiple projects match source quote {source_quote_number}")
                if linked:
                    payload["project_id"] = linked[0]["id"]
            invoice = client.request("/api/v1/finance/customer-invoices", method="POST", body=payload, expected=(201,))
            invoice_listing.append(invoice)
            operation = "created"
        _verify_invoice(invoice, record)
        invoice_evidence.append({
            "invoice_number": ref,
            "id": invoice["id"],
            "operation": operation,
            "project_id": invoice.get("project_id"),
            "status": invoice["status"],
            "total": invoice["total"],
        })

    return {
        **validation,
        "project": {
            "id": project["id"],
            "operation": project_operation,
            "status": project["status"],
            "project_number": project.get("project_number"),
        },
        "quotes": quote_evidence,
        "invoices": invoice_evidence,
        "production_verified": True,
    }


def load_bundle(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "import"))
    parser.add_argument("--input", required=True)
    parser.add_argument("--evidence")
    args = parser.parse_args(argv)
    bundle = load_bundle(args.input)
    if args.command == "validate":
        result = validate_bundle(bundle)
    else:
        if not args.evidence:
            parser.error("--evidence is required for import")
        result = import_bundle(bundle, IHOSClient())
        Path(args.evidence).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
