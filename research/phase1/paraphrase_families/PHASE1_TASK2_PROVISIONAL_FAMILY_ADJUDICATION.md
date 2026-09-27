# Phase 1 Task 2 — Provisional Paraphrase-Family Adjudication

## 1. Objective

This task semantically inspected the 99 lexical near-duplicate candidates produced by Phase 1 Task 1. Its purpose is to distinguish likely paraphrases from shared templates, related but different requests, label conflicts, and lexical false positives before any family-aware benchmark split is designed.

## 2. Important provenance

**Semantic judgments in this task were produced by Codex and are provisional, not human gold annotations.** Every decision is marked `adjudication_source = codex_provisional`. No source label, Phase 0 split, query text, or frozen Phase 0 artifact was changed. Final benchmark-grade membership remains pending human confirmation of the reduced review queue.

## 3. Pair decisions

| Provisional decision | Pairs |
| --- | ---: |
| `SAME_MEANING` | 42 |
| `SAME_TEMPLATE_DIFFERENT_MEANING` | 31 |
| `RELATED_NOT_PARAPHRASE` | 16 |
| `LABEL_CONFLICT_SAME_MEANING` | 7 |
| `AMBIGUOUS_REVIEW_REQUIRED` | 1 |
| `NOT_PARAPHRASE` | 2 |
| **Total** | **99** |

Confidence distribution: 84 `HIGH`, 14 `MEDIUM`, and 1 `LOW`.

Decision provenance and the allowed decision/confidence policy are defined in `paraphrase_adjudication_protocol_v1.md`. The Git-safe pair ledger contains identifiers and aggregate attributes only; raw query text remains outside Git.

## 4. Provisional families

The deterministic graph builder used only `SAME_MEANING` and `LABEL_CONFLICT_SAME_MEANING` as equivalence edges. All remaining samples received singleton family IDs.

- Total samples: 1,454
- Provisional equivalence edges: 49
- Total provisional families: 1,408
- Multi-row families: 42
- Singleton families: 1,366
- Largest family: 4 samples
- Transitivity review-required families: 2
- Label-conflict families: 6

Components larger than two samples were checked against every implied member pair. A missing or non-equivalent implied pair causes the whole component to be marked `HUMAN_REVIEW_REQUIRED`; equivalence is not forced transitively.

## 5. Cross-split family leakage

Under the unchanged Phase 0 split:

- Families crossing TRAIN–DEV: 8
- Families crossing TRAIN–TEST: 7
- Families crossing DEV–TEST: 0
- Families crossing all three splits: 0
- Samples affected by cross-split families: 33
- Same-label cross-split families: 13
- Cross-label cross-split families: 2

These counts describe provisional semantic families, not a revised split. No sample was moved.

## 6. Cross-label issues

- Exact source-label conflict groups carried forward from Task 1: 2
- Cross-label `SAME_MEANING` pairs: 1
- `LABEL_CONFLICT_SAME_MEANING` pairs: 7
- Provisional cross-label families: 6

The apparent conflicts are review targets only. No frozen label was corrected or otherwise changed.

## 7. Human review queue

- Private path: `D:\Files\Academic\4-1\NLP\NLP Project\NLP_Project-_private\phase1\human_review_queue_v1.csv`
- Rows: 29
- SHA-256: `104140c76c72b5a28abed48e641a8f35a64ca40fe0c5fc98340ceddbb1d2fcc2`
- Human decisions completed: no

The queue contains raw text and therefore remains outside Git. Its Git-safe index contains only sample/pair identifiers, labels, splits, similarity, provisional judgments, and review reasons.

## 8. Scientific interpretation

Lexical similarity is not semantic equivalence. An exact duplicate can be identified computationally, and lexical near-duplicate candidates can be ranked computationally, but a paraphrase family represents an information-need judgment. The provisional Codex decisions reduce the manual workload from 99 pairs to 29 targeted cases; they do not make the data human-audited.

The review queue is a moderate remaining manual task because it includes all non-high-confidence judgments, label-equivalence conflicts, unsafe transitive components, and consequential high-similarity cross-split cases. The final benchmark should use a family-aware split only after these cases are confirmed and a final adjudicated map is frozen.

## 9. Phase 1 impact

Phase 1 now has a complete provisional family assignment for all 1,454 samples, a reproducible graph builder, an aggregate leakage analysis, and a compact private review queue. Human confirmation, label-definition audit, annotation guidance, challenge-set design, and the final benchmark freeze remain pending. No benchmark split or model evaluation was created in this task.
