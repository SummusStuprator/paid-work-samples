# Shopify CSV preflight: keep sizes and images distinct

This small, read-only demo distinguishes repeated variant records from ordinary size/color rows and extra product images. It is AI-authored, uses synthetic data, and has not been run against any buyer's store. No Shopify access, installation or credentials are needed.

For a nontechnical walkthrough, open [preview.html](preview.html) in a browser. It uses four rows from the same synthetic sample to explain sizes, images and a conflicting record, followed by an example review milestone. It is a self-contained static page with no uploads, scripts, telemetry or live-store actions.

Run with Python 3.10 or later; no packages to install:

```sh
cd shopify-csv-preflight
python preflight.py sample-before.csv
python -m unittest -v
```

## See the example

[sample-before.csv](sample-before.csv) has eight synthetic rows. The generated [sample-report.json](sample-report.json) identifies four review items:

| CSV line | Observation | Suggested human decision |
|---|---|---|
| 5 | `demo-tee` repeats size S with a different SKU and price | Establish which source record is correct before any change |
| 7 | `demo-hoodie` uses SKU `003` for both L and XL | Check whether the shared SKU is intentional |
| 8 | `demo-cap` has SKU/price but no option identity | Check intended behavior before an existing-product update |
| 9 | No product handle | Identify the product; do not guess from title or SKU |

Lines 2–3 are separate tee sizes. Line 4 is an additional image, not another product or variant. None of these rows are removed. There is deliberately no automatically “fixed” file.

## How it decides

Variant comparison uses the exact product handle and the three option-value positions together. The same size at different handles remains separate. A repeated tuple is a review finding, not proof that the live store contains duplicate products. SKU is a string: `001` stays distinct from `1`. Reuse across variant keys is flagged for review, not rejected.

An additional-image row must contain only the handle, product image URL and optional image position/alt text. Missing identity, incomplete option pairs, inconsistent option names, and missing option dimensions used elsewhere on the same product receive their own findings. The tool does not silently fill names or transform identifiers.

Current and selected legacy headings are supported, including `URL handle`/`Handle`, `SKU`/`Variant SKU`, and `Option1 name`/`Option1 Name`. If both aliases occur, processing stops rather than guessing which wins. See `ALIASES` in [preflight.py](preflight.py) for the complete supported mapping. Unknown columns remain available but are not comprehensively validated.

Implementation preflight: the existing portfolio's CSV tools already use Python's standard `csv` parser. This demo reuses that parser and strict row/schema validation approach; the generic cleaner's automatic row-removal policy would be unsuitable here.

## Scope and limitations

This is an offline grouping and update-risk check, not a complete Shopify import validator or store diagnosis. It cannot determine whether separate handles should become one product, confirm live inventory, validate images, resolve metafield-linked options, or protect third-party variant-ID references. It does not contact image URLs. Product-only rows with no variant fields are not assumed to be default variants.

Shopify's [official CSV documentation](https://help.shopify.com/en/manual/products/import-export/using-csv), consulted September 12, 2026, describes distinct product, variant and image rows, retained support for older headers, and risks when option columns are absent during variant updates. This demo reports those missing-column situations for review; it never performs an update.

The input is opened read-only. Reports go to standard output: **never redirect to the source CSV path**, because the shell could truncate it before this program starts. Exit 0 means a full report was produced, including when findings exist. Exit 2 means parsing or schema validation failed, with no partial JSON. UTF-8 BOMs and quoted multiline fields are supported; references identify the physical line on which the record ends.

The default row limit is 100,000 (`--max-rows` changes it). This bounds record count, not total memory or file size. Reports may contain source identifiers; use synthetic samples for public sharing.

## A possible paid engagement

A separately agreed engagement could inspect one exported catalogue, identify how size/color records were split, and prepare a proposed change map with explicit acceptance checks. Catalogue size, import history, apps and backup/reversal needs determine scope. This sample is not a quote, promise of a full store rebuild, or authorization to merge/delete products.
