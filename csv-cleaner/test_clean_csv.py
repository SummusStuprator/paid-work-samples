import csv
import io
import tempfile
import unittest
from pathlib import Path

from clean_csv import clean_file, clean_stream


class CleanerTests(unittest.TestCase):
    def clean(self, text, **kwargs):
        output = io.StringIO(newline="")
        report = clean_stream(io.StringIO(text, newline=""), output, **kwargs)
        return list(csv.DictReader(io.StringIO(output.getvalue()))), report

    def test_deduplication_and_conflict_report(self):
        rows, report = self.clean(
            "order_id,customer_email,amount\n1,a@example.com,10\n"
            "1,a@example.com,10\n2,b@example.com,20\n1,a@example.com,99\n")
        self.assertEqual([r["amount"] for r in rows], ["10", "20"])
        self.assertEqual(report["duplicate_rows"], 2)
        self.assertEqual(report["conflicting_duplicates"], 1)
        self.assertEqual(report["issues"][0]["dropped_row"]["amount"], "99")

    def test_missing_fields_including_duplicate_rows(self):
        rows, report = self.clean(
            "order_id,customer_email,amount\n1,a@example.com,10\n"
            "1,,\n2,   ,5\n3,c@example.com,\n")
        missing = [i for i in report["issues"] if i["kind"] == "missing_value"]
        self.assertEqual([i["columns"] for i in missing],
                         [["customer_email", "amount"], ["customer_email"], ["amount"]])
        self.assertEqual(len(rows), 3)

    def test_empty_input(self):
        rows, report = self.clean("")
        self.assertEqual(rows, [])
        self.assertEqual(report["input_rows"], 0)
        self.assertEqual(report["issues"], [])

    def test_header_only(self):
        rows, report = self.clean("order_id,customer_email,amount\n")
        self.assertEqual(rows, [])
        self.assertEqual(report["output_rows"], 0)

    def test_custom_key_and_quoted_values(self):
        rows, report = self.clean('id,text\nx,"a,b\nc"\nx,"a,b\nc"\n', key="id", required=[])
        self.assertEqual(rows, [{"id": "x", "text": "a,b\nc"}])
        self.assertEqual(report["duplicate_rows"], 1)

    def test_blank_keys_are_not_collapsed(self):
        rows, report = self.clean("order_id,customer_email,amount\n,a,1\n,b,2\n")
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(report["issues"]), 2)

    def test_invalid_schema(self):
        for text in ["order_id,amount\n", "order_id,amount,amount\n", "order_id,,amount\n"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.clean(text)

    def test_bad_row_does_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/"in.csv", Path(folder)/"out.csv"
            source.write_text("order_id,customer_email,amount\n1,a,2,extra\n")
            output.write_text("existing output")
            with self.assertRaises(ValueError):
                clean_file(source, output)
            self.assertEqual(output.read_text(), "existing output")
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["in.csv", "out.csv"])

    def test_bom_and_in_place(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"orders.csv"
            path.write_text("order_id,customer_email,amount\n1,a,2\n1,a,2\n", encoding="utf-8-sig")
            report = clean_file(path, path)
            self.assertEqual(report["duplicate_rows"], 1)
            self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
