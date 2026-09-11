# Order matching: a small executable acceptance sample

Original AI-authored demonstration using synthetic records. It is not CaseKit code, a confirmed defect in any product, or a production Shopify integration.

Run on Node 22+ with `node --test match.test.cjs`. No packages, network calls, customer data or credentials required.

The selector distinguishes one candidate, ambiguity, no match and insufficient input. It does not select the first order when a buyer has several, fall back from a conflicting order reference, or collapse leading zeros. The supplied store identifier scopes candidates; the caller must separately establish authorization for that store. Email matching is NOT proof of identity or permission to expose order data.

Example: the fixture buyer has #0012 and #0013 in store A, plus #0012 in store B. An A-scoped query for #0012 selects a1; an email-only query reports ambiguity. A query for #9999 reports no match.

Policy choices requiring product agreement: this sample lowercases email, preserves plus aliases, matches store IDs and order numbers exactly, and treats duplicate rows as ambiguous. A real adapter must define pagination/completeness, stale data, ID canonicalization and authorization before this can be used in a product.

A proposed paid milestone is to adapt the agreed cases to one real matching function, using redacted fixtures, with a patch if a failure is demonstrated. No live system has been tested or changed.
