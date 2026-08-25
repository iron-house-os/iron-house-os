import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "ops" / "scripts" / "production_business_import.py"
SPEC = importlib.util.spec_from_file_location("production_business_import", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_bundle():
    return json.loads(
        (ROOT / "ops" / "production-business-imports" / "2026-08-25-coho-blueberry-vale.json").read_text()
    )


class BundleValidationTests(unittest.TestCase):
    def test_blueberry_bundle_validates(self):
        result = MODULE.validate_bundle(valid_bundle())
        self.assertTrue(result["validated"])
        self.assertEqual(result["quote_count"], 3)
        self.assertEqual(result["invoice_count"], 1)

    def test_project_cannot_enter_as_awarded(self):
        bundle = valid_bundle()
        bundle["project"]["payload"]["status"] = "awarded"
        with self.assertRaisesRegex(ValueError, "remain opportunities"):
            MODULE.validate_bundle(bundle)

    def test_quote_cannot_set_issue_status(self):
        bundle = valid_bundle()
        bundle["quotes"][0]["payload"]["issue_status"] = "issued"
        with self.assertRaisesRegex(ValueError, "API draft defaults"):
            MODULE.validate_bundle(bundle)

    def test_options_quote_total_excludes_mutually_exclusive_options(self):
        bundle = valid_bundle()
        options = bundle["quotes"][2]
        subtotal, gst, total = MODULE.quote_totals(options["payload"])
        self.assertEqual(str(subtotal), "9769.23")
        self.assertEqual(str(gst), "488.46")
        self.assertEqual(str(total), "10257.69")
        self.assertIn("must not be added together", options["payload"]["notes"])

    def test_total_mismatch_is_rejected(self):
        bundle = copy.deepcopy(valid_bundle())
        bundle["quotes"][0]["expected_total"] = "1.00"
        with self.assertRaisesRegex(ValueError, "totals mismatch"):
            MODULE.validate_bundle(bundle)

    def test_line_amounts_are_rounded_before_subtotal(self):
        payload = {
            "gst_rate": "5.00",
            "line_items": [
                {"quantity": "0.333", "unit_price": "1.00"},
                {"quantity": "0.333", "unit_price": "1.00"},
                {"quantity": "0.333", "unit_price": "1.00"},
            ],
        }
        subtotal, gst, total = MODULE.quote_totals(payload)
        self.assertEqual(str(subtotal), "0.99")
        self.assertEqual(str(gst), "0.05")
        self.assertEqual(str(total), "1.04")

    def test_dates_required_before_any_import_write(self):
        bundle = valid_bundle()
        del bundle["quotes"][0]["payload"]["quote_date"]
        with self.assertRaisesRegex(ValueError, "quote_date is required"):
            MODULE.validate_bundle(bundle)


class FakeClient:
    def __init__(self):
        self.projects = []
        self.quotes = []
        self.invoices = []
        self.logged_in = 0
        self.post_count = 0

    def login(self):
        self.logged_in += 1

    def request(self, path, method="GET", body=None, expected=(200,)):
        if method == "GET":
            if path == "/api/v1/projects":
                return {"items": copy.deepcopy(self.projects)}
            if path == "/api/v1/customer-quotes":
                return {"items": copy.deepcopy(self.quotes)}
            if path == "/api/v1/finance/customer-invoices":
                return {"items": copy.deepcopy(self.invoices)}
            raise AssertionError(path)

        self.post_count += 1
        if path == "/api/v1/projects":
            record = copy.deepcopy(body)
            record.update({"id": "project-1", "project_number": None})
            self.projects.append(record)
            return copy.deepcopy(record)
        if path == "/api/v1/customer-quotes":
            subtotal, gst, total = MODULE.quote_totals(body)
            record = copy.deepcopy(body)
            record.update({
                "id": f"quote-{len(self.quotes) + 1}",
                "quote_number": f"Q-2026-{len(self.quotes) + 1:03d}",
                "subtotal": str(subtotal),
                "gst": str(gst),
                "total": str(total),
                "status": "draft",
                "issue_status": "draft",
            })
            self.quotes.append(record)
            return copy.deepcopy(record)
        if path == "/api/v1/finance/customer-invoices":
            subtotal, gst, total = MODULE.invoice_totals(body)
            record = copy.deepcopy(body)
            record.update({
                "id": f"invoice-{len(self.invoices) + 1}",
                "subtotal": str(subtotal),
                "gst": str(gst),
                "total": str(total),
                "status": "draft",
            })
            self.invoices.append(record)
            return copy.deepcopy(record)
        raise AssertionError(path)


class ImportExecutionTests(unittest.TestCase):
    def test_import_is_idempotent_with_api_verification(self):
        client = FakeClient()
        first = MODULE.import_bundle(valid_bundle(), client)
        self.assertEqual(first["project"]["operation"], "created")
        self.assertTrue(all(item["operation"] == "created" for item in first["quotes"]))
        self.assertEqual(first["invoices"][0]["operation"], "created")
        self.assertEqual(client.post_count, 5)

        second = MODULE.import_bundle(valid_bundle(), client)
        self.assertEqual(second["project"]["operation"], "verified_existing")
        self.assertTrue(all(item["operation"] == "verified_existing" for item in second["quotes"]))
        self.assertEqual(second["invoices"][0]["operation"], "verified_existing")
        self.assertEqual(client.post_count, 5)
        self.assertEqual(client.logged_in, 2)

    def test_same_name_address_without_key_fails_before_write(self):
        client = FakeClient()
        project = copy.deepcopy(valid_bundle()["project"]["payload"])
        project["id"] = "conflict"
        project["metadata"] = {}
        client.projects.append(project)
        with self.assertRaisesRegex(RuntimeError, "manual review required"):
            MODULE.import_bundle(valid_bundle(), client)
        self.assertEqual(client.post_count, 0)


if __name__ == "__main__":
    unittest.main()
