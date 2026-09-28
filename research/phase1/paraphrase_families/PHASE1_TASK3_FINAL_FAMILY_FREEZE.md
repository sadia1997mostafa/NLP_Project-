# Phase 1 Task 3 — Final Paraphrase-Family Freeze

## 1. Objective

Paraphrase-family grouping is frozen before benchmark construction so semantically equivalent queries can be kept in the same future split. This prevents a benchmark from overstating generalization through cross-split paraphrase leakage.

## 2. Candidate audit

Phase 1 Task 1 identified 99 lexical near-duplicate candidate pairs among the 1,454 frozen Phase 0 samples. Lexical similarity was used only to identify review candidates; it was not treated as semantic equivalence by itself.

## 3. Human review

- Targeted high-risk or ambiguous pair cases reviewed by a human: 29
- Mandatory human correction applied: 1
- Corrected pair: NID5-ND-000048
- Component-level human reviews: 1
- Samples in the component review: 4
- Pair relations covered by the component review: 6
- Lower-risk candidate decisions retaining machine assistance: 70

The 29 pair-reviewed cases and the six component relations overlap. These counts describe different review scopes and must not be added together as unique human-reviewed pairs.

## 4. Human correction

For NID5-ND-000048:

- Original human decision: RELATED_NOT_PARAPHRASE
- Corrected human decision: LABEL_CONFLICT_SAME_MEANING
- Reason: identical normalized text appeared under conflicting frozen source labels.

No source label was changed.

## 5. Component-level review

Pairwise review originally produced one transitivity conflict: equivalence edges connected four samples even though other reviewed relations inside that component were non-equivalent. The four queries were therefore presented together and assigned to semantic groups rather than reviewed independently again.

The human-approved partition was:

- Group A: NID5-V1-000769, NID5-V1-000826
- Group B: NID5-V1-000894, NID5-V1-001449

Authoritative family-equivalence relations:

- Equivalent: NID5-ND-000056, NID5-ND-000071
- Not equivalent: NID5-ND-000057, NID5-ND-000058, NID5-ND-000067, NID5-ND-000068

Semantic decision provenance is retained separately. In particular, earlier machine semantic judgments for NID5-ND-000057 and NID5-ND-000067 remain recorded, while family membership follows the human component review.

## 6. Final decision distribution

Semantic decisions across the 99 candidates:

| Decision | Count |
| --- | ---: |
| SAME_MEANING | 39 |
| LABEL_CONFLICT_SAME_MEANING | 3 |
| SAME_TEMPLATE_DIFFERENT_MEANING | 38 |
| RELATED_NOT_PARAPHRASE | 17 |
| NOT_PARAPHRASE | 2 |

Family-equivalence decisions:

- EQUIVALENT: 40
- NOT_EQUIVALENT: 59

## 7. Final family statistics

| Measure | Final |
| --- | ---: |
| Samples | 1,454 |
| Families | 1,414 |
| Multi-row families | 40 |
| Singleton families | 1,374 |
| Largest family | 2 |
| Label-conflict families | 3 |
| Families with human-confirmed evidence | 14 |
| Human-only multi-row components | 14 |
| Codex-only multi-row components | 26 |
| Mixed-provenance components | 0 |

Compared with the provisional map, total families increased from 1,408 to 1,414, multi-row families decreased from 42 to 40, singleton families increased from 1,366 to 1,374, and the largest family decreased from four samples to two.

## 8. Cross-split family leakage

- TRAIN–DEV families: 8
- TRAIN–TEST families: 5
- DEV–TEST families: 0
- Families spanning more than two splits: 0
- Samples affected by cross-split families: 26
- Same-label cross-split families: 12
- Cross-label cross-split families: 1

The provisional map affected 33 cross-split samples; the final human-consistent map affects 26. The frozen Phase 0 split itself was not changed.

## 9. Label conflicts and provenance

Three final families contain more than one frozen source label. These are recorded as LABEL_CONFLICT_FAMILY; no relabeling was performed.

Pair-level semantic provenance distinguishes human_confirmed decisions from codex_provisional decisions. Family-equivalence provenance separately records human_pair_review, human_component_review, or codex_provisional. The final family map therefore preserves the distinction between semantic annotation and graph membership.

## 10. Scientific limitation

This is targeted human review plus machine assistance, not independent dual annotation of all 99 candidate pairs or all 1,454 examples. Twenty-nine high-risk or ambiguous pair cases received human review, one four-sample transitivity conflict received component-level human review, and the remaining lower-risk candidate decisions retain machine-assisted provenance. This limitation must be reported accurately in later research documentation.

## 11. Benchmark implication

The final map is now suitable for family-aware benchmark split construction, provided its machine-assisted provenance is reported. No benchmark split, challenge set, model training, or model evaluation was performed in this task.
