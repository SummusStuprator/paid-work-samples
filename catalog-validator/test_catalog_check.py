import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from catalog_check import inspect_catalog

HEADER = "supplier,sku,description,unit,pack_quantity\n"


class CatalogTests(unittest.TestCase):
    def inspect(self, rows, **options):
        return inspect_catalog(io.StringIO(HEADER + rows, newline=""), **options)

    def test_same_sku_at_different_suppliers_and_leading_zeros_stay_distinct(self):
        result = self.inspect("A,001,Bolt,each,1\nB,001,Bolt,each,1\nA,1,Bolt,each,1\n")
        self.assertEqual(result["distinct_exact_product_keys"], 3)
        self.assertEqual(result["findings"], [])

    def test_conflicting_pack_is_not_treated_as_exact_duplicate(self):
        result = self.inspect("A,001,Bolt,each,1\nA,001,Bolt,box,12\nA,001,Bolt,each,1\n")
        conflict, duplicate = result["findings"]
        self.assertEqual(conflict["kind"], "conflicting_product_rows")
        self.assertEqual(conflict["columns"], ["unit", "pack_quantity"])
        self.assertEqual((conflict["line"], conflict["first_line"]), (3, 2))
        self.assertEqual(duplicate["kind"], "exact_duplicate_row")
        self.assertEqual(result["rows_checked"], 3)

    def test_near_identifiers_flagged_without_merging(self):
        result = self.inspect("A,ab-01,Bolt,each,1\n A ,AB-01 ,Bolt,each,1\n")
        self.assertEqual(result["distinct_exact_product_keys"], 2)
        self.assertEqual(result["counts_by_kind"], {"possible_identifier_collision": 1})

    def test_blank_keys_do_not_form_product_groups(self):
        result = self.inspect("A,,Bolt,each,1\nA,,Nut,box,2\n")
        self.assertEqual(result["distinct_exact_product_keys"], 0)
        self.assertEqual(result["counts_by_kind"], {"missing_required_value": 2})

    def test_quantity_policy_rejects_ambiguous_and_nonfinite_values(self):
        for quantity in ("0", "-1", "NaN", "Infinity", "1e3", '"1,5"', "1_000"):
            with self.subTest(quantity=quantity):
                result = self.inspect(f"A,1,Bolt,each,{quantity}\n")
                self.assertEqual(result["counts_by_kind"], {"invalid_pack_quantity": 1})
        self.assertEqual(self.inspect("A,1,Cable,m,0.25\n")["findings"], [])

    def test_multiline_csv_line_reference_and_optional_field_conflict(self):
        data = 'supplier,sku,description,unit,pack_quantity,finish\nA,1,"Bolt\nsteel",each,1,zinc\nA,1,"Bolt\nsteel",each,1,plain\n'
        result = inspect_catalog(io.StringIO(data, newline=""))
        self.assertEqual(result["findings"][0]["columns"], ["finish"])
        self.assertEqual(result["findings"][0]["line"], 5)
        self.assertEqual(result["findings"][0]["first_line"], 3)

    def test_incomplete_or_oversize_input_does_not_produce_success(self):
        for data in ("", "sku,sku\n1,1\n", HEADER + "A,1,Bolt,each\n", HEADER + 'A,1,"unfinished'):
            with self.subTest(data=data), self.assertRaises((ValueError, __import__('csv').Error)):
                inspect_catalog(io.StringIO(data, newline=""))
        with self.assertRaises(ValueError):
            self.inspect("A,1,Bolt,each,1\nA,2,Nut,each,1\n", max_rows=1)

    def test_cli_bom_support_and_source_unchanged_on_success_and_failure(self):
        script = Path(__file__).with_name("catalog_check.py")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "catalog.csv"
            for content, expected_code in ((HEADER + "A,001,Bolt,each,1\n", 0), (HEADER + "bad\n", 2)):
                original = content.encode("utf-8-sig")
                source.write_bytes(original)
                result = subprocess.run([sys.executable, str(script), str(source)], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected_code)
                self.assertEqual(source.read_bytes(), original)
                if expected_code == 0:
                    self.assertEqual(json.loads(result.stdout)["rows_checked"], 1)
                else:
                    self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
