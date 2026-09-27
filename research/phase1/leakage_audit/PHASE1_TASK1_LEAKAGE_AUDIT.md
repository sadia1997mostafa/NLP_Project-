# Phase 1 Task 1 — Leakage and Near-Duplicate Audit

## 1. Objective

Leakage auditing precedes challenge-set design so that exact duplication,
superficial lexical overlap, label conflicts, and candidate repeated frames can
be measured without changing the frozen Phase 0 split. Similarity creates
review candidates; it does not automatically define semantic families.

## 2. Frozen input

- Protocol: `NID-5CLASS-PHASE0-V1`
- Rows: 1,454
- Source SHA-256: `6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa`
- Split-manifest SHA-256: `4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1`
- Phase 0 verification: PASS
- Phase 0 artifacts modified: no
- Model evaluations performed: zero

## 3. Exact duplicates

The frozen Phase 0 normalization and `AUDIT-NORM-V1` both produce 7 exact
duplicate groups involving 14 rows. Five groups are same-label and two are
cross-label conflicts. No exact group crosses a Phase 0 split. The
punctuation-light representation produces the same counts, so the prior Phase
0 finding is fully reconciled.

## 4. Near-duplicate statistics

Character 3–5-gram TF-IDF over punctuation-light audit text yields 99 unique
unordered candidate pairs at cosine >= 0.80.

| Similarity band | Total | Same split | Cross split | Same label | Cross label |
|---|---:|---:|---:|---:|---:|
| >= 0.95 | 9 | 8 | 1 | 7 | 2 |
| 0.90–0.95 | 15 | 8 | 7 | 8 | 7 |
| 0.85–0.90 | 20 | 10 | 10 | 8 | 12 |
| 0.80–0.85 | 55 | 33 | 22 | 43 | 12 |

Token-set Jaccard and `difflib.SequenceMatcher` ratios are retained as
secondary lexical diagnostics. No threshold is declared a final family rule.

## 5. Cross-split candidates

Counts below are cumulative thresholds.

| Threshold | TRAIN–DEV | TRAIN–TEST | DEV–TEST | All cross split |
|---|---:|---:|---:|---:|
| >= 0.95 | 1 | 0 | 0 | 1 |
| >= 0.90 | 2 | 6 | 0 | 8 |
| >= 0.85 | 5 | 12 | 1 | 18 |
| >= 0.80 | 16 | 21 | 3 | 40 |

At >= 0.80, 22 cross-split pairs share a label and 18 cross labels. These are
near-duplicate / lexical leakage candidates pending review, not proof of
semantic leakage.

## 6. TEST-to-TRAIN similarity

Maximum character-TFIDF similarity from each held-out row to TRAIN:

| Split | Mean | Median | P90 | P95 | Maximum |
|---|---:|---:|---:|---:|---:|
| DEV | 0.592711 | 0.599159 | 0.765751 | 0.807134 | 0.961050 |
| TEST | 0.602471 | 0.605585 | 0.789945 | 0.835731 | 0.943476 |

## 7. Label conflicts

There are two exact cross-label groups and two exact cross-label pairs. Across
the lexical candidates there are 2 cross-label pairs at >= 0.95, 9 at >= 0.90,
21 at >= 0.85, and 33 at >= 0.80. No label was changed or adjudicated.

## 8. Template-like candidate families

Aggregate pattern checks find 12 long-prefix pairs, 34 long-suffix pairs, 22
few-token-substitution pairs, and 15 near-identical-frame pairs. Connecting the
latter produces 15 two-row candidate families; 3 cross splits and 4 cross
labels. These are template-like lexical family candidates only. The audit does
not establish whether any text was generated, nor does it establish semantic
paraphrase identity.

## 9. Interpretation

An **exact duplicate** has an identical normalized-text hash. A **lexical
near-duplicate candidate** exceeds an audit similarity threshold. A true
**paraphrase family** requires human semantic review; lexical similarity alone
cannot declare one.

## 10. Implication for Phase 1 benchmark design

Assessment: **MODERATE lexical leakage risk**. Exact-duplicate containment is
sound, and only one cross-split pair reaches 0.95. Nevertheless, 8 cross-split
pairs reach 0.90 and 40 reach 0.80, including 21 TRAIN–TEST candidates at the
lowest audit threshold. Manual adjudication is warranted before any final
challenge split is designed. The Phase 0 split remains unchanged.

## 11. Private review artifact

- Path: `D:\Files\Academic\4-1\NLP\NLP Project\NLP_Project-_private\phase1\near_duplicate_review_v1.csv`
- Rows: 99
- SHA-256: `de072833e6a0b8df51426b2155af1fd6007f9579baf1087f1ae0e5859cd04062`
- Git tracked: no

Raw query text appears only in this external private review file. Review
decision and notes fields are intentionally blank.

## 12. Next research step

Human reviewers should adjudicate the highest-risk candidates into genuine
paraphrase families before the final challenge-set design begins.
