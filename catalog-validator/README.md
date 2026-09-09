# Supplier catalog preflight sample

A Python standard-library tool that reads a CSV and produces a JSON report before someone imports it into a catalog. AI-authored and tested. The bundled data are entirely synthetic; this is not a Matterhaul integration or a claim about any vendor's defects.

```sh
python catalog_check.py sample.csv
python -m unittest -v
```

The sample has eight rows and five findings: an exact duplicate, a conflicting product record, a zero pack quantity, a missing SKU, and a possible case/whitespace collision. The same SKU at a different supplier is not a duplicate. SKU `001` stays a string, distinct from `1`.

Required headers: `supplier`, `sku`, `description`, `unit`, `pack_quantity`. Additional fields are retained for comparison. Product identity uses the exact `(supplier, sku)` pair. Differences in additional fields also count as conflicts. Conflicts are compared with the first occurrence of the exact product key. Exact duplicate rows may also trigger a conflict finding if they repeat a later, conflicting version.

Case folding and trimming are used only to flag possible identifier collisions for review; the tool never merges them. Units are compared as source text, not interpreted or converted. Pack quantities must use positive plain decimal syntax (`12` or `0.25`); locale-dependent separators, exponents, signed values and nonfinite values are rejected under this sample's explicit policy. Unit-specific rules require an agreed supplier specification.

The tool opens the source read-only and writes the report to standard output. It supports UTF-8 BOM and quoted multiline fields; line references identify the physical line where a CSV record ends. Do not redirect the report to the input path: shell redirection can truncate that file before Python starts.

Exit 0 means a complete report was generated, even if findings exist. Exit 2 means the input/schema could not be processed completely; no JSON report is emitted. Empty files are rejected; header-only catalogs yield a complete zero-row report. A default 100,000-row limit bounds row count, not byte size or individual field lengths. Configure it with `--max-rows`. Memory grows with records and findings; large catalogs need a database-backed implementation.

This sample does not validate supplier authority, currency, price, cross-system identity, or physical equivalence of differently named units. All findings require a business decision before any source data are changed.
