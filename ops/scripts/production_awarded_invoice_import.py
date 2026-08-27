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
import urllib.parse
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
    completed_work_records = bundle.get("completed_work_records")
    require(isinstance(completed_work_records, list), "completed_work_records must be a list")
    require(len(completed_work_records) == len(payload["line_items"]), "completed-work count must match invoice line-item count")
    source_line_keys: set[str] = set()
    completed_work_total = Decimal("0")
    for position, (completed_work, invoice_line) in enumerate(
        zip(completed_work_records, payload["line_items"], strict=True),
        start=1,
    ):
        require(completed_work.get("record_type") == "completed_work", "completed-work record_type must be completed_work")
        require(not completed_work.get("project_id"), "completed-work bundle records must not supply project_id")
        require("status" not in completed_work, "completed-work records must use the API recorded status")
        details = completed_work.get("details") or {}
        line_key = str(details.get("source_line_key") or "")
        require(bool(line_key), "completed-work source_line_key is required")
        require(line_key not in source_line_keys, f"duplicate completed-work source_line_key: {line_key}")
        source_line_keys.add(line_key)
        require(details.get("source_line_position") == position, "completed-work source line position mismatch")
        require(details.get("source_import_key") == bundle["import_key"], "completed-work source import key mismatch")
        require(details.get("source_invoice_number") == ref, "completed-work source invoice mismatch")
        require(details.get("source_drive_file_id") == metadata["source_drive_file_id"], "completed-work source Drive file mismatch")
        require(details.get("source_invoice_date") == payload["invoice_date"], "completed-work source invoice date mismatch")
        require(completed_work.get("title") == invoice_line["description"], "completed-work title must match invoice line")
        require(details.get("description") == invoice_line["description"], "completed-work description must match invoice line")
        require(Decimal(str(details.get("quantity"))) == Decimal(str(invoice_line["quantity"])), "completed-work quantity must match invoice line")
        require(Decimal(str(details.get("billable_rate"))) == Decimal(str(invoice_line["unit_price"])), "completed-work billable rate must match invoice line")
        line_amount = money(Decimal(str(details["quantity"])) * Decimal(str(details["billable_rate"])))
        require(money(details.get("billable_amount")) == line_amount, "completed-work billable amount mismatch")
        require(details.get("cost_status") == "internal_cost_unverified", "completed-work internal cost must remain unverified")
        require(details.get("revenue_trace_only") is True, "completed work must be revenue trace only")
        require(not {"actual_cost", "actual_cost_amount", "internal_cost_amount", "internal_cost_rate"}.intersection(details), "completed work cannot include unverified actual-cost values")
        source_work_date = details.get("source_work_date")
        if source_work_date:
            require(details.get("record_date_basis") == "source_work_date", "source work dates require source_work_date basis")
            require(completed_work.get("work_date") == source_work_date, "completed-work date must match source work date")
        else:
            require(details.get("record_date_basis") == "invoice_date_reference_only", "undated source lines must use invoice-date reference basis")
            require(completed_work.get("work_date") == payload["invoice_date"], "invoice-date reference must use invoice date")
        completed_work_total += line_amount
    require(money(completed_work_total) == expected[0], "completed-work total must match invoice subtotal")
    return {
        "issue_number": bundle["issue_number"],
        "import_key": bundle["import_key"],
        "project_count": 1,
        "invoice_count": 1,
        "completed_work_count": len(completed_work_records),
        "completed_work_billable_total": str(money(completed_work_total)),
        "validated": True,
    }


class IHOSClient:
    def __init__(self) -> None:
        port = os.environ.get("IHOS_PORT", "8080")
        self.base = f"http://127.0.0.1:{port}"
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(self, path: str, method: str = "GET", body: dict[str, Any] | None = None, expected: tuple[int, ...] = (200,)) -> Any:
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


def verify_completed_work(record: dict[str, Any], payload: dict[str, Any], project_id: Any) -> None:
    expected = {
        "record_type": "completed_work",
        "project_id": str(project_id),
        "work_date": payload["work_date"],
        "title": payload["title"],
        "status": "recorded",
        "severity": payload.get("severity", "none"),
        "cost_code": payload.get("cost_code"),
        "employee_id": payload.get("employee_id"),
        "equipment_id": payload.get("equipment_id"),
        "supplier_id": payload.get("supplier_id"),
        "details": payload["details"],
        "document_ids": payload.get("document_ids", []),
        "signatures": payload.get("signatures", []),
        "alert_recipients": payload.get("alert_recipients", []),
    }
    actual = dict(record)
    actual["project_id"] = str(actual.get("project_id"))
    mismatches = [field for field, value in expected.items() if actual.get(field) != value]
    if mismatches:
        line_key = payload["details"]["source_line_key"]
        raise RuntimeError(f"Completed-work source line {line_key} differs in: {', '.join(mismatches)}")


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

    query = urllib.parse.urlencode({"project_id": project["id"], "source_import_key": bundle["import_key"]})
    existing_records = client.request(f"/api/v1/field-operations/completed-work?{query}")
    if not isinstance(existing_records, list):
        raise RuntimeError("Completed-work lookup returned an invalid response")
    existing_by_key: dict[str, dict[str, Any]] = {}
    for existing in existing_records:
        line_key = str((existing.get("details") or {}).get("source_line_key") or "")
        if not line_key:
            raise RuntimeError("Completed-work lookup returned a record without source_line_key")
        if line_key in existing_by_key:
            raise RuntimeError(f"Multiple completed-work records match source line {line_key}")
        existing_by_key[line_key] = existing
    expected_keys = {item["details"]["source_line_key"] for item in bundle["completed_work_records"]}
    unexpected_keys = sorted(set(existing_by_key) - expected_keys)
    if unexpected_keys:
        raise RuntimeError(f"Unexpected completed-work source lines require manual review: {unexpected_keys}")

    completed_results: list[dict[str, Any]] = []
    for completed_payload in bundle["completed_work_records"]:
        line_key = completed_payload["details"]["source_line_key"]
        existing = existing_by_key.get(line_key)
        if existing is not None:
            verify_completed_work(existing, completed_payload, project["id"])
            completed_results.append({"id": existing["id"], "source_line_key": line_key, "operation": "verified_existing"})
            continue
        create_payload = dict(completed_payload)
        create_payload["project_id"] = project["id"]
        created = client.request(
            "/api/v1/field-operations/records",
            method="POST",
            body=create_payload,
            expected=(201,),
        )
        verify_completed_work(created, completed_payload, project["id"])
        completed_results.append({"id": created["id"], "source_line_key": line_key, "operation": "created"})

    return {
        **validation,
        "project": {"id": project["id"], "operation": project_operation, "job_number": job_number, "status": project["status"]},
        "invoice": {"id": invoice["id"], "operation": invoice_operation, "invoice_number": ref, "status": invoice["status"], "total": invoice["total"]},
        "completed_work": {
            "created": sum(item["operation"] == "created" for item in completed_results),
            "verified_existing": sum(item["operation"] == "verified_existing" for item in completed_results),
            "records": completed_results,
            "billable_total": validation["completed_work_billable_total"],
            "cost_status": "internal_cost_unverified",
        },
        "production_verified": True,
    }


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
