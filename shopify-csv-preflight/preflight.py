"""Report Shopify CSV variant risks without changing or importing the source."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


# Current Shopify headings and selected older export headings. Unknown columns
# remain intact; no guessed normalization of product or SKU identifiers occurs.
ALIASES = {
    "Handle": "URL handle", "Variant SKU": "SKU",
    "Variant Price": "Price", "Variant Compare At Price": "Compare-at price",
    "Variant Grams": "Weight value (grams)",
    "Variant Inventory Qty": "Inventory quantity",
    "Variant Inventory Tracker": "Inventory tracker",
    "Variant Inventory Policy": "Continue selling when out of stock",
    "Variant Fulfillment Service": "Fulfillment service",
    "Variant Requires Shipping": "Requires shipping",
    "Variant Taxable": "Charge tax", "Variant Weight Unit": "Weight unit for display",
    "Variant Image": "Variant image URL", "Variant Barcode": "Barcode",
    "Image Src": "Product image URL", "Image Position": "Image position",
    "Image Alt Text": "Image alt text",
}
for _index in range(1, 4):
    ALIASES[f"Option{_index} Name"] = f"Option{_index} name"
    ALIASES[f"Option{_index} Value"] = f"Option{_index} value"

IMAGE_COLUMNS = {"Product image URL", "Image position", "Image alt text"}
VARIANT_COLUMNS = {
    "SKU", "Price", "Compare-at price", "Cost per item", "Barcode", "Barcodes",
    "Weight value (grams)", "Weight unit for display", "Inventory quantity",
    "Inventory tracker", "Continue selling when out of stock", "Fulfillment service",
    "Requires shipping", "Charge tax", "Variant image URL",
}


def inspect_csv(source, max_rows=100_000):
    """Use strict standard-library CSV parsing; line numbers are record-end lines."""
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    reader = csv.DictReader(source, strict=True)
    raw_headers = reader.fieldnames
    if (not raw_headers or any(not value.strip() for value in raw_headers)
            or len(raw_headers) != len(set(raw_headers))):
        raise ValueError("CSV requires unique, nonempty headers")
    headers = [ALIASES.get(value, value) for value in raw_headers]
    if len(headers) != len(set(headers)):
        raise ValueError("Current and legacy headers refer to the same column")
    if "URL handle" not in headers:
        raise ValueError("This grouping preflight needs URL handle (or legacy Handle)")
    if "Barcode" in headers and "Barcodes" in headers:
        raise ValueError("Barcode and Barcodes cannot both be present")

    findings, variants, names, sku_owners, product_rows, image_rows = [], {}, {}, {}, set(), []
    handles, option_rows, active_options = set(), [], {}
    rows_checked = variant_rows = 0

    def flag(kind, line, **details):
        findings.append({"kind": kind, "line": line, **details})

    variant_fields = sorted(set(headers) & VARIANT_COLUMNS)
    # Market-specific pricing is variant data too.
    variant_fields += [h for h in headers if h.startswith(("Price / ", "Compare-at price / "))]
    missing_option_headers = [h for h in ("Option1 name", "Option1 value") if h not in headers]
    if variant_fields and missing_option_headers:
        flag("variant_update_missing_option_columns", 1,
             columns=missing_option_headers,
             message="Review before updating existing products: variant columns lack option identity.")

    for rows_checked, raw in enumerate(reader, 1):
        if rows_checked > max_rows:
            raise ValueError(f"CSV exceeds max_rows={max_rows}; report is incomplete")
        line = reader.line_num
        if None in raw or any(value is None for value in raw.values()):
            raise ValueError(f"Wrong number of fields in row ending at line {line}")
        row = {ALIASES.get(key, key): value for key, value in raw.items()}
        handle = row["URL handle"]
        if not handle.strip():
            flag("missing_handle", line)
            continue  # Never combine unidentified rows.
        handles.add(handle)
        nonempty = {key for key, value in row.items() if value.strip()}
        if (row.get("Product image URL", "").strip()
                and nonempty <= {"URL handle", *IMAGE_COLUMNS}):
            image_rows.append((handle, line))
            continue
        product_rows.add(handle)

        populated_variant_fields = [key for key in variant_fields if row.get(key, "").strip()]
        option_values = tuple(row.get(f"Option{i} value", "") for i in range(1, 4))
        option_names = tuple(row.get(f"Option{i} name", "") for i in range(1, 4))
        if not any(value.strip() for value in (*option_values, *option_names)):
            if populated_variant_fields:
                flag("variant_data_without_options", line, handle=handle,
                     columns=populated_variant_fields)
            continue
        variant_rows += 1
        option_rows.append((handle, line, option_values, option_names))
        slots = active_options.setdefault(handle, set())
        slots.update(i for i, (name, value) in enumerate(zip(option_names, option_values))
                     if name.strip() or value.strip())

        valid_identity = bool(option_values[0].strip())
        if not valid_identity:
            flag("missing_first_option_value", line, handle=handle)
        for index, (name, value) in enumerate(zip(option_names, option_values), 1):
            if bool(name.strip()) != bool(value.strip()):
                flag("incomplete_option_pair", line, handle=handle, option=index)
                if not value.strip():
                    valid_identity = False
            if index > 1 and value.strip() and not option_values[index - 2].strip():
                flag("option_gap", line, handle=handle, option=index)
                valid_identity = False
            if name.strip():
                name_key = (handle, index)
                if name_key in names and names[name_key][0] != name:
                    flag("inconsistent_option_name", line, handle=handle, option=index,
                         first_line=names[name_key][1])
                else:
                    names.setdefault(name_key, (name, line))

        if not valid_identity:
            continue
        identity = (handle, option_values)
        if identity in variants:
            first_row, first_line = variants[identity]
            compared = [h for h in headers if h in VARIANT_COLUMNS or h.startswith("Option")
                        or h.startswith(("Price / ", "Compare-at price / "))]
            changed = [h for h in compared if row[h] != first_row[h]]
            flag("repeated_variant_tuple", line, handle=handle, values=list(option_values),
                 first_line=first_line, changed_variant_columns=changed)
        else:
            variants[identity] = (row, line)

        sku = row.get("SKU", "")
        if sku.strip():
            previous = sku_owners.setdefault(sku, (identity, line))
            if previous[0] != identity:
                flag("sku_used_by_multiple_variant_keys", line, handle=handle,
                     sku=sku, first_line=previous[1])

    for handle, line, values, option_names in option_rows:
        absent = [i + 1 for i in sorted(active_options[handle])
                  if not values[i].strip() and not option_names[i].strip()]
        if absent:
            flag("missing_options_used_elsewhere_on_product", line, handle=handle,
                 options=absent)
    for handle, line in image_rows:
        if handle not in product_rows:
            flag("image_handle_has_no_product_row_in_file", line, handle=handle,
                 message="May be an intentional update to an existing product; verify target.")
    return {
        "schema_version": 1,
        "rows_checked": rows_checked,
        "distinct_handles": len(handles),
        "variant_rows": variant_rows,
        "distinct_variant_keys": len(variants),
        "additional_image_rows": len(image_rows),
        "finding_count": len(findings),
        "counts_by_kind": dict(sorted(Counter(f["kind"] for f in findings).items())),
        "line_reference": "Physical CSV line where a record ends; header is line 1.",
        "policy": "Review only. No import, merge, deletion, normalization or store access.",
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--max-rows", type=int, default=100_000)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8-sig", newline="") as source:
            report = inspect_csv(source, args.max_rows)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
