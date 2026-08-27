#!/usr/bin/env python3
"""Validate and import one owner-approved awarded project plus draft customer invoice.

The project is created with status=awarded and without a supplied project_number so IHOS
allocates the permanent job number through its normal generator. The invoice remains draft.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

MONEY = Decimal("0.01")
JOB_RE = re.compile(r"^IH\d{7,}$")


def money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def invoice_totals(payload: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = money(sum(Decimal(str(x["quantity"])) * Decimal(str(x["unit_price"])) for x in payload["line_items"]))
    gst = money(subtotal * Decimal(str(payload.get("gst_rate", "5.00"))) / Decimal("100"))
    return subtotal, gst, money(subtotal + gst)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    require(bundle.get("schema_version") == 1, "schema_version must be 1")
    require(isinstance(bundle.get("issue_number"), int), "issue_number is required")
    require(bool(bundle.get("import_key")), "import_key is required")
    project = (bundle.get("project") or {}).get("payload") or {}
    require(project.get("status") == "awarded", "project must enter as awarded")
    require(not project.get("project_number"), "bundle must not supply a job number")
    require(project.get("name") and project.get("client_owner") and project.get("project_address"), "project identity is required")
    metadata = project.get("metadata") or {}
    require(metadata.get("source_import_key") == bundle["import_key"], "project metadata must carry source_import_key")
    require(metadata.get("source_drive_file_id"), "project metadata must carry source_drive_file_id")
    require(metadata.get("source_drive_modified_at"), "project metadata must carry source_drive_modified_at")
    invoice = bundle.get("invoice") or {}
    ref = invoice.get("external_reference")
    payload = invoice.get("payload") or {}
    require(ref and payload.get("invoice_number") == ref, "invoice external reference must match invoice_number")
    require(metadata.get("source_invoice_number") == ref, "project metadata source invoice must match invoice reference")
    require("status" not in payload, "invoice must use API draft default")
    require(payload.get("customer_name") and payload.get("customer_address") and payload.get("line_items"), "invoice billing and line items are required")
    require(payload.get("project_name") and payload.get("invoice_date") and payload.get("due_date") and payload.get("terms"), "invoice project, dates and terms are required")
    require(all(Decimal(str(item["quantity"])) > 0 for item in payload["line_items"]), "invoice quantities must be positive")
    calculated = invoice_totals(payload)
    expected = tuple(money(invoice[k]) for k in ("expected_subtotal", "expected_gst", "expected_total"))
    require(calculated == expected, f"invoice totals mismatch: calculated={calculated}, expected={expected}")
    return {"issue_number": bundle["issue_number"], "import_key": bundle["import_key"], "project_count": 1, "invoice_count": 1, "validated": True}


class IHOSClient:
    def __init__(self) -> None:
        port = os.environ.get("IHOS_PORT", "8080")
        self.base = f"http://127.0.0.1:{port}"
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(self, path: str, method: str = "GET", body: dict[str, Any] | None = None, expected: tuple[int, ...] = (200,)) -> dict[str, Any]:
        request = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(), method=method, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=30) as response:
                result = json.load(response)
                if response.status not in expected:
                    raise RuntimeError(f"Unexpected status {response.status}")
                return result
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"IHOS request failed: {exc.code} {exc.read().decode(errors='replace')}") from exc

    def login(self) -> None:
        result = self.request("/api/v1/auth/login", method="POST", body={"email": os.environ["BOOTSTRAP_ADMIN_EMAIL"], "password": os.environ["BOOTSTRAP_ADMIN_PASSWORD"]})
        if result.get("authentication") != "authenticated":
            raise RuntimeError("IHOS login did not authenticate")


def verify_job_number(value: Any) -> str:
    number = str(value or "").strip()
    if "-" in number or not JOB_RE.fullmatch(number):
        raise RuntimeError(f"Generated IHOS job number is invalid: {number!r}")
    return number


def import_bundle(bundle: dict[str, Any], client: IHOSClient) -> dict[str, Any]:
    validation = validate_bundle(bundle)
    client.login()
    project_payload = bundle["project"]["payload"]
    projects = client.request("/api/v1/projects").get("items", [])
    matches = [p for p in projects if (p.get("metadata") or {}).get("source_import_key") == bundle["import_key"]]
    if len(matches) > 1:
        raise RuntimeError("Multiple projects match source_import_key")
    if matches:
        project = matches[0]
        project_operation = "verified_existing"
    else:
        conflicts = [p for p in projects if p.get("name") == project_payload["name"] and p.get("project_address") == project_payload["project_address"]]
        if conflicts:
            raise RuntimeError("Same-name/same-address project exists without import key; manual review required")
        project = client.request("/api/v1/projects", method="POST", body=project_payload, expected=(201,))
        project_operation = "created"
    if project.get("status") != "awarded":
        raise RuntimeError("Imported project is not awarded")
    if (project.get("metadata") or {}).get("source_import_key") != bundle["import_key"]:
        raise RuntimeError("Project import key verification failed")
    job_number = verify_job_number(project.get("project_number"))

    record = bundle["invoice"]
    ref = record["external_reference"]
    invoices = client.request("/api/v1/finance/customer-invoices").get("items", [])
    matches = [x for x in invoices if x.get("invoice_number") == ref]
    if len(matches) > 1:
        raise RuntimeError(f"Multiple invoices match {ref}")
    if matches:
        invoice = matches[0]
        invoice_operation = "verified_existing"
    else:
        payload = dict(record["payload"])
        payload["project_id"] = project["id"]
        invoice = client.request("/api/v1/finance/customer-invoices", method="POST", body=payload, expected=(201,))
        invoice_operation = "created"
    if str(invoice.get("project_id")) != str(project["id"]):
        raise RuntimeError("Invoice is not linked to the imported project")
    if invoice.get("status") != "draft":
        raise RuntimeError("Invoice must remain draft")
    for field, expected in (("subtotal", record["expected_subtotal"]), ("gst", record["expected_gst"]), ("total", record["expected_total"])):
        if str(invoice.get(field)) != str(expected):
            raise RuntimeError(f"Invoice {field} mismatch")
    return {**validation, "project": {"id": project["id"], "operation": project_operation, "job_number": job_number, "status": project["status"]}, "invoice": {"id": invoice["id"], "operation": invoice_operation, "invoice_number": ref, "status": invoice["status"], "total": invoice["total"]}, "production_verified": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "import"))
    parser.add_argument("--input", required=True)
    parser.add_argument("--evidence")
    args = parser.parse_args(argv)
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
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
