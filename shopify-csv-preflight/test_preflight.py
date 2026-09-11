import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from preflight import inspect_csv


HEADERS = ["URL handle", "Title", "Option1 name", "Option1 value",
           "Option2 name", "Option2 value", "SKU", "Price",
           "Product image URL", "Image position"]


def stream(rows, headers=HEADERS):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    text.seek(0)
    return text


def variant(handle="tee", size="S", sku="001", **extra):
    return {"URL handle": handle, "Title": "Example tee", "Option1 name": "Size",
            "Option1 value": size, "SKU": sku, "Price": "25.00", **extra}


class PreflightTests(unittest.TestCase):
    def test_variants_and_additional_images_are_not_duplicates(self):
        rows = [variant(), variant(size="M", sku="002", Title=""),
                {"URL handle": "tee", "Product image URL": "https://example.com/back.jpg",
                 "Image position": "2"}]
        result = inspect_csv(stream(rows))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["distinct_variant_keys"], 2)
        self.assertEqual(result["additional_image_rows"], 1)

    def test_repeated_tuple_reports_conflicting_sku_and_price(self):
        result = inspect_csv(stream([variant(), variant(sku="009", Price="29.00")]))
        finding = result["findings"][0]
        self.assertEqual(finding["kind"], "repeated_variant_tuple")
        self.assertEqual(finding["first_line"], 2)
        self.assertEqual(finding["line"], 3)
        self.assertEqual(finding["changed_variant_columns"], ["SKU", "Price"])

    def test_repeated_identical_tuple_is_still_reported(self):
        result = inspect_csv(stream([variant(), variant()]))
        self.assertEqual(result["findings"][0]["changed_variant_columns"], [])

    def test_all_option_positions_belong_to_key(self):
        rows = [variant(**{"Option2 name": "Color", "Option2 value": "Red"}),
                variant(sku="002", **{"Option2 name": "Color", "Option2 value": "Blue"})]
        result = inspect_csv(stream(rows))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["distinct_variant_keys"], 2)

    def test_handles_scope_variants_and_sku_is_not_numeric(self):
        result = inspect_csv(stream([variant(sku="001"), variant(handle="other", sku="1")]))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["distinct_variant_keys"], 2)

    def test_third_option_distinguishes_variants_and_missing_dimension_is_flagged(self):
        headers = HEADERS + ["Option3 name", "Option3 value"]
        dimensions = {"Option2 name": "Color", "Option2 value": "Red", "Option3 name": "Fit"}
        rows = [variant(**dimensions, **{"Option3 value": "Regular"}),
                variant(sku="002", **dimensions, **{"Option3 value": "Tall"})]
        result = inspect_csv(stream(rows, headers))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["distinct_variant_keys"], 2)
        result = inspect_csv(stream([variant(sku="003"), *rows], headers))
        self.assertEqual(result["counts_by_kind"], {"missing_options_used_elsewhere_on_product": 1})
        self.assertEqual(result["findings"][0]["options"], [2, 3])

    def test_same_sku_at_distinct_keys_is_review_candidate(self):
        result = inspect_csv(stream([variant(), variant(size="M")]))
        self.assertEqual(result["counts_by_kind"], {"sku_used_by_multiple_variant_keys": 1})
        self.assertEqual(result["findings"][0]["sku"], "001")

    def test_missing_option_headers_with_sku_gets_update_warning(self):
        result = inspect_csv(stream([{"URL handle": "tee", "SKU": "001"}],
                                    ["URL handle", "SKU"]))
        self.assertIn("variant_update_missing_option_columns", result["counts_by_kind"])
        self.assertIn("variant_data_without_options", result["counts_by_kind"])
        self.assertEqual(result["distinct_variant_keys"], 0)

    def test_present_but_empty_options_are_not_assumed_default_variant(self):
        result = inspect_csv(stream([{"URL handle": "cap", "SKU": "001", "Price": "10"}]))
        self.assertEqual(result["counts_by_kind"], {"variant_data_without_options": 1})

    def test_legacy_schema_matches_current_results(self):
        old = ["Handle", "Title", "Option1 Name", "Option1 Value", "Variant SKU",
               "Variant Price", "Image Src"]
        result = inspect_csv(stream([
            {"Handle": "tee", "Option1 Name": "Size", "Option1 Value": "S", "Variant SKU": "001"},
            {"Handle": "tee", "Image Src": "https://example.com/extra.jpg"},
        ], old))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["additional_image_rows"], 1)

    def test_ambiguous_aliases_and_duplicate_headers_fail(self):
        for content in ("Handle,URL handle\na,b\n", "Handle,Handle\na,b\n",
                        "Handle,\na,b\n", "Handle,Barcode,Barcodes\na,b,c\n"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                inspect_csv(io.StringIO(content))

    def test_malformed_csv_fails_instead_of_partial_report(self):
        for content in ("Handle,Title\nx\n", "Handle,Title\nx,y,z\n",
                        'Handle,Title\nx,"unterminated\n'):
            with self.subTest(content=content), self.assertRaises((ValueError, csv.Error)):
                inspect_csv(io.StringIO(content))

    def test_multiline_physical_line_references(self):
        result = inspect_csv(stream([variant(Title="Two\nlines"), variant()]))
        self.assertEqual(result["findings"][0]["first_line"], 3)
        self.assertEqual(result["findings"][0]["line"], 4)

    def test_unidentified_rows_not_combined(self):
        result = inspect_csv(stream([variant(handle=""), variant(handle="")]))
        self.assertEqual(result["counts_by_kind"], {"missing_handle": 2})
        self.assertEqual(result["distinct_variant_keys"], 0)

    def test_inconsistent_option_names_and_gaps_need_review(self):
        result = inspect_csv(stream([variant(), variant(size="M", sku="002",
                                                      **{"Option1 name": "Color"})]))
        self.assertIn("inconsistent_option_name", result["counts_by_kind"])
        gap = variant(**{"Option1 value": "", "Option2 name": "Size", "Option2 value": "S"})
        result = inspect_csv(stream([gap]))
        self.assertIn("option_gap", result["counts_by_kind"])
        self.assertEqual(result["distinct_variant_keys"], 0)

    def test_orphan_image_is_review_only_even_if_row_appears_first(self):
        image = {"URL handle": "tee", "Product image URL": "https://example.com/a.jpg"}
        self.assertEqual(inspect_csv(stream([image, variant()]))["findings"], [])
        self.assertEqual(inspect_csv(stream([image]))["counts_by_kind"],
                         {"image_handle_has_no_product_row_in_file": 1})

    def test_header_only_and_row_limit(self):
        self.assertEqual(inspect_csv(stream([]))["rows_checked"], 0)
        with self.assertRaises(ValueError):
            inspect_csv(stream([variant(), variant(size="M")]), max_rows=1)
        with self.assertRaises(ValueError):
            inspect_csv(stream([]), max_rows=0)

    def test_cli_bom_source_preserved_and_invalid_input_has_no_json(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "source.csv"
            original = stream([variant()]).getvalue().encode("utf-8-sig")
            target.write_bytes(original)
            command = [sys.executable, str(Path(__file__).with_name("preflight.py")), str(target)]
            result = subprocess.run(command, text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout)["finding_count"], 0)
            self.assertEqual(target.read_bytes(), original)
            target.write_text("Handle,Title\na,b,c\n", encoding="utf-8")
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
