"""Read a supplier catalog CSV and report data-quality findings without editing it."""

import argparse
import csv
import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = ("supplier", "sku", "description", "unit", "pack_quantity")


def inspect_catalog(source, max_rows=100_000):
    """Return findings with physical CSV line references; preserve identifiers exactly."""
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    reader = csv.DictReader(source, strict=True)
    columns = reader.fieldnames
    if not columns or any(not c.strip() for c in columns) or len(set(columns)) != len(columns):
        raise ValueError("CSV needs unique, nonempty headers")
    missing_columns = [c for c in REQUIRED if c not in columns]
    if missing_columns:
        raise ValueError("Missing columns: " + ", ".join(missing_columns))
    findings, exact_rows, identities, normalized = [], {}, {}, {}
    row_count = 0

    def flag(kind, line, **details):
        findings.append({"kind": kind, "line": line, **details})

    for row_count, row in enumerate(reader, 1):
        if row_count > max_rows:
            raise ValueError(f"Catalog exceeds max_rows={max_rows}; no complete report produced")
        line = reader.line_num
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"Wrong number of fields in row ending at line {line}")
        missing = [c for c in REQUIRED if not row[c].strip()]
        if missing:
            flag("missing_required_value", line, columns=missing)

        quantity = row["pack_quantity"]
        if quantity.strip():
            # Use decimal syntax only. Reject exponents, grouping separators and
            # nonfinite tokens instead of guessing a supplier's number convention.
            valid_syntax = re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", quantity.strip())
            try:
                valid_quantity = bool(valid_syntax) and Decimal(quantity.strip()) > 0
            except InvalidOperation:
                valid_quantity = False
            if not valid_quantity:
                flag("invalid_pack_quantity", line, value=quantity)

        signature = tuple(row[c] for c in columns)
        if signature in exact_rows:
            flag("exact_duplicate_row", line, first_line=exact_rows[signature])
        else:
            exact_rows[signature] = line

        identity = (row["supplier"], row["sku"])
        if not all(v.strip() for v in identity):
            continue  # Blank identifiers never establish a product identity.
        first = identities.get(identity)
        if first is None:
            identities[identity] = (row, line)
        else:
            previous, first_line = first
            changed = [c for c in columns if c not in ("supplier", "sku") and row[c] != previous[c]]
            if changed:
                flag("conflicting_product_rows", line, first_line=first_line,
                     supplier=identity[0], sku=identity[1], columns=changed)

        candidate = tuple(v.strip().casefold() for v in identity)
        candidates = normalized.setdefault(candidate, {})
        if identity not in candidates:
            if candidates:
                earlier_identity, earlier_line = next(iter(candidates.items()))
                flag("possible_identifier_collision", line, first_line=earlier_line,
                     supplier=identity[0], sku=identity[1],
                     earlier_supplier=earlier_identity[0], earlier_sku=earlier_identity[1])
            candidates[identity] = line

    return {
        "schema_version": 1,
        "rows_checked": row_count,
        "distinct_exact_product_keys": len(identities),
        "finding_count": len(findings),
        "counts_by_kind": dict(sorted(Counter(f["kind"] for f in findings).items())),
        "line_reference": "Physical CSV line where the record ends; header is line 1.",
        "policy": "Report only. No records merged, units converted, or source values changed.",
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--max-rows", type=int, default=100_000)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8-sig", newline="") as source:
            report = inspect_catalog(source, max_rows=args.max_rows)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
