# Passport Pilot Semantic Review Audit

Owner: Prothom / Prothom

Service: `PASSPORT`

Taxonomy version: `0.2.0`

Pilot rows: 224

Review status: `PASSED`

## Review coverage

Every pilot row was reviewed for naturalness, Passport context, parent and
leaf correctness, specificity, neighboring-label risk, language style,
priority, difficulty, family independence, mutable-fact safety, privacy
safety, and whether the leaf should be retained.

| Review group | Rows | PASS | REWRITE |
|---|---:|---:|---:|
| MANDATORY | 28 | 21 | 7 |
| BOUNDARY | 49 | 9 | 40 |
| STANDARD | 147 | 147 | 0 |
| **Total** | **224** | **177** | **47** |

No row required `RELABEL` or `TAXONOMY_REVIEW`. All 56 leaves were retained.

## Standard-row audit

The 147 STANDARD rows were inspected programmatically and semantically,
grouped by parent and leaf. A targeted scan checked for contrastive,
annotation-engineered language such as “X না”, “specifically”, “not X but
Y”, and broad wording that might conceal a more specific leaf.

The flagged STANDARD phrases were legitimate parts of their intent, such as
asking whether NID is mandatory, reporting that payment failed, or stating
that information will remain unchanged during reissue. They did not
artificially rule out neighboring labels. All 147 STANDARD rows therefore
passed without rewrite.

## Rewrites

The 47 approved rewrites remove classifier-facing contrastive cues from
MANDATORY and BOUNDARY examples while preserving:

- row IDs;
- parent and query-topic IDs;
- independent `parent_query_id` families;
- priority, language style, difficulty, provenance, privacy, and OOD labels.

The rewritten text in the review worksheet and canonical pilot CSV is
identical. No duplicate normalized text was introduced.

## Provisional-leaf decisions

The seven mandatory pilot-review leaves were retained:

- `PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC`
- `PASSPORT_DOCUMENTS_MISSING`
- `PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC`
- `PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM`
- `PASSPORT_APPOINTMENT_PROBLEM`
- `PASSPORT_APPLICATION_DELAY`
- `PASSPORT_GENERAL_SERVICE_GUIDANCE`

Their four independent families form coherent citizen needs after the
approved wording changes. General service guidance remains a real
orientation intent and must never be used as an OOD or low-confidence
fallback.

## Result

`PASS`

The Passport pilot contains 224 reviewed independent synthetic seeds across
56 leaves. Structural and review validators pass. The Passport taxonomy is
locally ready for future shared-contract review, but
`shared_contract_frozen` remains `false` and no model training is authorized.
