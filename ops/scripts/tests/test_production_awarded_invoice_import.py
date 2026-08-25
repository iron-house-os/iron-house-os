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


class AwardedInvoiceImportTests(unittest.TestCase):
    def test_bowline_bundle_validates(self):
        result = MODULE.validate_bundle(valid_bundle())
        self.assertTrue(result["validated"])
        self.assertEqual(result["project_count"], 1)
        self.assertEqual(result["invoice_count"], 1)

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

    def test_job_number_rejects_hyphens(self):
        with self.assertRaisesRegex(RuntimeError, "invalid"):
            MODULE.verify_job_number("IH-2026-001")
        self.assertEqual(MODULE.verify_job_number("IH2026001"), "IH2026001")


if __name__ == "__main__":
    unittest.main()
