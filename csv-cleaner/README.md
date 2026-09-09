# CSV deduplication and validation

Python 3, standard library only. Created with an AI coding assistant.

```sh
python clean_csv.py orders.csv cleaned.csv --key order_id
python -m unittest -v
```

The command prints a JSON report to stdout. Redirect it to a separate report
file if needed. Missing email and amount values are flagged, not fabricated.
Change those checks with `--required field1 field2`, or use `--required` alone
to check only the key.

The first row for each exact, case-sensitive key is retained. Later rows with
that key are removed; if their other fields differ, the complete removed row
is recorded as a conflict in the report. Blank keys are retained separately
and flagged. This is a keep-first policy, not a merge or an assumption that
the newest row is correct. Whitespace-only required values count as missing.

Malformed headers and rows cause exit code 2. Output is replaced atomically
after parsing succeeds, preserving an existing output on validation failure.
UTF-8 BOM input and quoted multiline fields are supported. Empty input yields
an empty output and a zero-row summary. Memory grows with distinct keys and
validation findings; use external sorting/database tooling for very large files.

Validation checks missing values, header uniqueness and row width; it does not
claim to verify email deliverability, currency values, or business rules.
