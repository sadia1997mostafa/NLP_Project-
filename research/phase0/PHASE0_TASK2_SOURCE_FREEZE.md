# Phase 0 Task 2 — NID Five-Class Source Freeze

## 1. Scope

This is a **new canonical reproducible baseline**, not a reconstruction of the
lost historical experiment. The remembered 96.36% IID and 82.64% shifted
Macro-F1 values remain unverified references.

## 2. Frozen source identity

- Source: `G:\My Drive\NID Query Datasheet.gsheet`
- Content-identical Drive copy: `G:\My Drive\Copy of NID Query Datasheet.gsheet`
- Sheet: `Sheet1`
- Private snapshot: sibling `NLP_Project-_private/phase0/nid_5class_source_v1.csv`
- Rows: 1,454
- Physical CSV columns: 15 (13 named plus 2 unnamed trailing columns)
- Rows with populated unnamed trailing cells: 17
- Raw SHA-256: `6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa`
- Canonical content SHA-256: `156d0a6a5f1f15773cc2adf286fc7e9f1c7d5f68fe8f332757a7435bc0c68811`

Canonical content hashing serializes an object containing the full ordered raw
header (including both unnamed columns) and all ordered 15-cell rows as compact
UTF-8 JSON (`ensure_ascii=false`, no key sorting). This separates semantic cell
content from CSV quoting/newline serialization. The raw values in the unnamed
columns remain private and are not interpreted as model fields.

## 3. Privacy screen

The aggregate-only heuristic screen flagged 0 rows. No matched value or
raw query text is stored in Git metadata. Manual review recommended:
`TRUE`. A zero heuristic result is
not proof that no sensitive free-form information exists; the raw snapshot
remains private.

The two unnamed trailing columns are populated in the same 17 rows. Aggregate
inspection found ASCII alphabetic text, not numeric-only or identifier-like
values. Neither column is used as query text, label, split feature, or baseline
model input. Their status is
`REQUIRES_OWNER_REVIEW_BEFORE_PUBLIC_RELEASE`; values remain private and are
still covered by the frozen full-row hashes.

## 4. Label freeze

| ID | Label | Count |
|---:|---|---:|
| 0 | `NID Information Correction` | 267 |
| 1 | `New NID Registration` | 448 |
| 2 | `Lost/Stolen NID` | 236 |
| 3 | `NID Online Problem` | 305 |
| 4 | `Smart ID Card` | 198 |

Total: **1,454**. The Sheet's `parent_id` values are not used as class IDs.

## 5. Canonical normalization

Input is converted to string, normalized to Unicode NFC, consecutive whitespace
is collapsed, and leading/trailing whitespace is stripped. No lowercasing,
transliteration, punctuation/number removal, stemming, stopword removal,
aggressive Bangla normalization, or augmentation is applied.

## 6. Duplicate handling

- Exact normalized duplicate groups: 7
- Rows involved: 14
- Cross-label conflict groups: 2
- Status: **LABEL CONFLICT**

Conflicting labels are preserved without repair. Every exact normalized-text
group is assigned wholly to one split.

## 7. Split algorithm

Protocol `NID-5CLASS-PHASE0-V1` uses seed 42 and target proportions 70/15/15.
Groups are exact normalized-text hashes. Cross-label and larger groups are
considered first; remaining order is a seeded SHA-256 order. Each group is
greedily placed in the split minimizing target overshoot and normalized squared
deviation from per-label and overall largest-remainder targets. SHA-256 provides
a deterministic tie-break. No model output or expected score affects assignment.

- Train: 1017
- DEV: 219
- TEST: 218

| Label | Train | DEV | TEST |
|---|---:|---:|---:|
| `NID Information Correction` | 187 | 40 | 40 |
| `New NID Registration` | 314 | 67 | 67 |
| `Lost/Stolen NID` | 165 | 36 | 35 |
| `NID Online Problem` | 213 | 46 | 46 |
| `Smart ID Card` | 138 | 30 | 30 |

- Cross-split normalized-text overlap: 0
- Manifest SHA-256: `4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1`
- Deterministic in-process rerun: PASS

## 8. Evaluation contract

Train only on `train`, select/tune only on `dev`, and evaluate final IID results
once on `test`. Macro-F1 is primary; accuracy, macro precision/recall,
per-class metrics and the confusion matrix are secondary. TEST is prohibited
for model or threshold selection.

## 9. Historically unknown

The historical split, seed, preprocessing, label encoder, training command,
model/checkpoint, predictions, confusion matrix and shifted dataset remain
unknown. This freeze does not claim to recover them.

## 10. Deferred to Phase 1

Phase 1 will construct and freeze independently specified distribution-shift
challenge sets and perform deeper paraphrase-family/near-duplicate leakage
auditing. No shift set is created here.
