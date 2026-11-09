import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "ops" / "scripts" / "production_awarded_invoice_import.py"
SPEC = importlib.util.spec_from_file_location("production_awarded_invoice_import", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_bundle():
    return json.loads((ROOT / "ops" / "production-awarded-invoice-imports" / "2026-08-25-bowline-rawlison.json").read_text())


class FakeClient:
    def __init__(self) -> None:
        self.projects = []
        self.invoices = []
        self.completed_work = []
        self.logged_in = False

    def login(self):
        self.logged_in = True

    def request(self, path, method="GET", body=None, expected=(200,)):
        assert self.logged_in
        if path == "/api/v1/projects" and method == "GET":
            return {"items": copy.deepcopy(self.projects)}
        if path == "/api/v1/projects" and method == "POST":
            record = {
                **copy.deepcopy(body),
                "id": "project-1",
                "project_number": "IH2026001",
            }
            self.projects.append(record)
            return copy.deepcopy(record)
        if path == "/api/v1/finance/customer-invoices" and method == "GET":
            return {"items": copy.deepcopy(self.invoices)}
        if path == "/api/v1/finance/customer-invoices" and method == "POST":
            subtotal, gst, total = MODULE.invoice_totals(body)
            record = {
                **copy.deepcopy(body),
                "id": "invoice-1",
                "status": "draft",
                "subtotal": str(subtotal),
                "gst": str(gst),
                "total": str(total),
            }
            self.invoices.append(record)
            return copy.deepcopy(record)
        if path.startswith("/api/v1/field-operations/completed-work?") and method == "GET":
            return copy.deepcopy(self.completed_work)
        if path == "/api/v1/field-operations/records" and method == "POST":
            record = {
                **copy.deepcopy(body),
                "id": f"completed-{len(self.completed_work) + 1}",
                "status": "recorded",
                "severity": body.get("severity", "none"),
                "cost_code": body.get("cost_code"),
                "employee_id": body.get("employee_id"),
                "equipment_id": body.get("equipment_id"),
                "supplier_id": body.get("supplier_id"),
                "document_ids": body.get("document_ids", []),
                "signatures": body.get("signatures", []),
                "alert_recipients": body.get("alert_recipients", []),
            }
            self.completed_work.append(record)
            return copy.deepcopy(record)
        raise AssertionError(f"Unexpected request: {method} {path}")


class AwardedInvoiceImportTests(unittest.TestCase):
    def test_bowline_bundle_validates(self):
        result = MODULE.validate_bundle(valid_bundle())
        self.assertTrue(result["validated"])
        self.assertEqual(result["project_count"], 1)
        self.assertEqual(result["invoice_count"], 1)
        self.assertEqual(result["issue_number"], 353)
        self.assertEqual(result["completed_work_count"], 7)
        self.assertEqual(result["completed_work_billable_total"], "10622.40")

    def test_bundle_cannot_supply_job_number(self):
        bundle = valid_bundle()
        bundle["project"]["payload"]["project_number"] = "IH2026999"
        with self.assertRaisesRegex(ValueError, "must not supply a job number"):
            MODULE.validate_bundle(bundle)

    def test_project_must_enter_awarded(self):
        bundle = valid_bundle()
        bundle["project"]["payload"]["status"] = "opportunity"
        with self.assertRaisesRegex(ValueError, "must enter as awarded"):
            MODULE.validate_bundle(bundle)

    def test_invoice_total_mismatch_fails_closed(self):
        bundle = copy.deepcopy(valid_bundle())
        bundle["invoice"]["expected_total"] = "1.00"
        with self.assertRaisesRegex(ValueError, "totals mismatch"):
            MODULE.validate_bundle(bundle)

    def test_final_drive_revision_is_staged_exactly(self):
        bundle = valid_bundle()
        project = bundle["project"]["payload"]
        invoice = bundle["invoice"]
        payload = invoice["payload"]
        metadata = project["metadata"]
        self.assertEqual(metadata["source_drive_file_id"], "1laUuqBbgcU5ck8rIz0Qd3N-Gd6I8U5ZS")
        self.assertEqual(metadata["source_drive_modified_at"], "2026-08-27T00:41:46.422Z")
        self.assertEqual(payload["customer_name"], "Zakaria Tadrous")
        self.assertEqual(payload["due_date"], "2026-08-15")
        self.assertEqual(payload["terms"], "Due upon receipt")
        self.assertEqual([item["unit_price"] for item in payload["line_items"][:4]], ["220.00"] * 4)
        self.assertEqual(invoice["expected_subtotal"], "10622.40")
        self.assertEqual(invoice["expected_gst"], "531.12")
        self.assertEqual(invoice["expected_total"], "11153.52")

    def test_source_provenance_is_required(self):
        bundle = valid_bundle()
        del bundle["project"]["payload"]["metadata"]["source_drive_file_id"]
        with self.assertRaisesRegex(ValueError, "source_drive_file_id"):
            MODULE.validate_bundle(bundle)

    def test_completed_work_must_match_invoice_and_cannot_invent_actual_cost(self):
        bundle = valid_bundle()
        bundle["completed_work_records"][0]["details"]["billable_amount"] = "1.00"
        with self.assertRaisesRegex(ValueError, "billable amount mismatch"):
            MODULE.validate_bundle(bundle)

        bundle = valid_bundle()
        bundle["completed_work_records"][0]["details"]["internal_cost_amount"] = "1000.00"
        with self.assertRaisesRegex(ValueError, "actual-cost"):
            MODULE.validate_bundle(bundle)

    def test_import_creates_then_verifies_all_completed_work_idempotently(self):
        client = FakeClient()
        first = MODULE.import_bundle(valid_bundle(), client)
        self.assertEqual(first["completed_work"]["created"], 7)
        self.assertEqual(first["completed_work"]["verified_existing"], 0)
        self.assertEqual(first["completed_work"]["billable_total"], "10622.40")
        self.assertEqual(first["completed_work"]["cost_status"], "internal_cost_unverified")
        self.assertEqual(len(client.completed_work), 7)

        second = MODULE.import_bundle(valid_bundle(), client)
        self.assertEqual(second["project"]["operation"], "verified_existing")
        self.assertEqual(second["invoice"]["operation"], "verified_existing")
        self.assertEqual(second["completed_work"]["created"], 0)
        self.assertEqual(second["completed_work"]["verified_existing"], 7)
        self.assertEqual(len(client.completed_work), 7)

    def test_import_fails_closed_when_source_line_key_content_differs(self):
        client = FakeClient()
        MODULE.import_bundle(valid_bundle(), client)
        client.completed_work[0]["title"] = "Conflicting historical claim"
        with self.assertRaisesRegex(RuntimeError, "differs in: title"):
            MODULE.import_bundle(valid_bundle(), client)

    def test_job_number_rejects_hyphens(self):
        with self.assertRaisesRegex(RuntimeError, "invalid"):
            MODULE.verify_job_number("IH-2026-001")
        self.assertEqual(MODULE.verify_job_number("IH2026001"), "IH2026001")


if __name__ == "__main__":
    unittest.main()
