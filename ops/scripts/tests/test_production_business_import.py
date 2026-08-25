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


if __name__ == "__main__":
    unittest.main()
