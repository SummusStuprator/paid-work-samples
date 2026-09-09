"""Deduplicate CSV by a named key, keeping the first row and reporting issues."""

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path


def clean_stream(source, destination, key="order_id", required=("customer_email", "amount")):
    """Write cleaned rows; return counts and source-line validation findings.

    Keys compare exactly, without stripping or case folding. Blank keys are
    retained and flagged, since unrelated unidentified rows must not be merged.
    Repeated keys keep the first row. Conflicting rows are recorded in full in
    the report so a changed order is not silently lost. Missing values are
    reported even on rows removed as duplicates.
    """
    reader = csv.DictReader(source, strict=True)
    fields = reader.fieldnames
    report = dict(input_rows=0, output_rows=0, duplicate_rows=0,
                  conflicting_duplicates=0, issues=[])
    if fields is None:
        return report
    if len(fields) != len(set(fields)) or any(not f.strip() for f in fields):
        raise ValueError("Headers must be nonempty and unique")
    absent = [f for f in (key, *required) if f not in fields]
    if absent:
        raise ValueError("Missing columns: " + ", ".join(absent))
    writer = csv.DictWriter(destination, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    seen = {}
    for row in reader:
        report["input_rows"] += 1
        line = reader.line_num
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"CSV row ending at line {line} has the wrong column count")
        missing = [f for f in dict.fromkeys((key, *required)) if not row[f].strip()]
        if missing:
            report["issues"].append(dict(line=line, kind="missing_value", columns=missing))
        identity = row[key]
        if identity.strip() and identity in seen:
            report["duplicate_rows"] += 1
            previous, previous_line = seen[identity]
            if row != previous:
                report["conflicting_duplicates"] += 1
                report["issues"].append(dict(
                    line=line, kind="conflicting_duplicate", key=identity,
                    retained_line=previous_line, dropped_row=row))
            continue
        if identity.strip():
            seen[identity] = (row, line)
        writer.writerow(row)
        report["output_rows"] += 1
    return report


def clean_file(input_path, output_path, **options):
    """Replace output only after successful validation; support in-place use."""
    target = Path(output_path)
    temp_path = None
    try:
        with open(input_path, encoding="utf-8-sig", newline="") as source:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", dir=target.parent,
                prefix=".csv-clean-", suffix=".tmp", delete=False
            ) as destination:
                temp_path = destination.name
                report = clean_stream(source, destination, **options)
        os.replace(temp_path, target)
        temp_path = None
        return report
    finally:
        if temp_path is not None:
            os.unlink(temp_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--key", default="order_id")
    parser.add_argument("--required", nargs="*", default=["customer_email", "amount"])
    args = parser.parse_args()
    try:
        report = clean_file(args.input, args.output, key=args.key, required=args.required)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
