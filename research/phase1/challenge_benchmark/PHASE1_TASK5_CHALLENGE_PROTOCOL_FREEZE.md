# Phase 1 Task 5 — Challenge Protocol Freeze

## 1. Objective

This task freezes the design of `NID5-SHIFT-V1`, an evaluation-only five-class benchmark for measuring robustness to controlled linguistic and surface-form distribution shifts. It freezes dependencies, eligibility, leakage protection, coverage strata, future deterministic selection, transformation conditions, semantic review, provenance, and planned metrics before any seed selection or challenge generation.

Status: **SCHEMA_FROZEN_V1**.

## 2. Why matched challenge evaluation

Every future seed will appear once in each condition C0–C4. Holding the underlying citizen need, source seed, canonical label, and family constant makes condition differences easier to interpret than comparisons between unrelated samples. Macro-F1 can be compared on balanced matched panels, and prediction consistency, flip rate, and recovery rate can be computed seed by seed.

Matched design does not eliminate generation or reviewer bias. It provides a controlled robustness comparison, not a representative population estimate of all Bangladeshi citizen language.

## 3. Frozen seed target

The future panel contains 100 unique semantic seeds drawn only from frozen Phase 0 TEST:

| Label | Target seeds |
|---|---:|
| NID Information Correction | 20 |
| New NID Registration | 20 |
| Lost/Stolen NID | 20 |
| NID Online Problem | 20 |
| Smart ID Card | 20 |
| **Total** | **100** |

Each seed will later receive C0 ORIGINAL, C1 NATURAL_PARAPHRASE, C2 BANGLISH_SCRIPT_SHIFT, C3 CODE_MIXED, and C4 TYPO_NOISE, producing 500 matched instances. This task selected no seeds.

## 4. Eligible TEST pool

The frozen TEST population contains 218 rows. Structural family/conflict filtering yields 211 eligible rows across 209 eligible family units. A seed quota consumes at most one row from each family.

| Label | TEST total | Eligible rows | Eligible family units | Required | Feasible |
|---|---:|---:|---:|---:|---|
| NID Information Correction | 40 | 40 | 38 | 20 | YES |
| New NID Registration | 67 | 65 | 65 | 20 | YES |
| Lost/Stolen NID | 35 | 34 | 34 | 20 | YES |
| NID Online Problem | 46 | 44 | 44 | 20 | YES |
| Smart ID Card | 30 | 28 | 28 | 20 | YES |

Aggregate exclusions are five TEST rows whose families cross TRAIN, zero whose families cross DEV, two TEST rows in the source-conflict register, and zero other deterministic metadata/text failures.

This feasibility profile does not replace semantic review. Before final seed freeze, each deterministically proposed candidate must be human-confirmed as `CLASSIFIABLE`, explicit enough under `FROZEN_V1`, and suitable for meaning-preserving transformation. Rejected candidates are skipped in stable order without relabeling. If that gate ever leaves fewer than 20 in a class, selection must stop rather than lower the quota.

## 5. Leakage protection

- Seeds come only from Phase 0 TEST.
- Any family containing TRAIN or DEV is excluded.
- Only one seed may be selected from a family.
- All six historical source-conflict samples are ineligible; two occur in TEST and are excluded by the current profile.
- Variants inherit the seed family and evaluation-only status.
- Neither challenge text nor results may be used for training, augmentation, model selection, threshold tuning, or iterative repair presented as final evaluation.

## 6. Five benchmark conditions

| Condition | Name | Role |
|---|---|---|
| C0 | ORIGINAL | unchanged matched control |
| C1 | NATURAL_PARAPHRASE | natural reformulation with the same information need |
| C2 | BANGLISH_SCRIPT_SHIFT | plausible Latin-script Banglish rendering |
| C3 | CODE_MIXED | natural Bengali-English or Banglish-English mixing |
| C4 | TYPO_NOISE | one to three localized realistic surface perturbations where possible |

Latin-dominant script is only a deterministic surface profile and is not treated as proof of Banglish. C1–C3 require human naturalness approval. C4 must remain readable and preserve decisive entities and action.

## 7. Semantic-preservation rules

Every shifted variant preserves the canonical coarse label, requested action, lifecycle stage, critical entity relations, polarity, first-issuance/replacement distinction, correction/portal distinction, and human-frozen Smart Card boundary.

Any variant that changes the intent, becomes ambiguous, adds unstated conditions, drops boundary-critical information, introduces a conflicting lifecycle, or becomes unnatural/unintelligible is rewritten or rejected. It is never repaired by changing its label.

## 8. Human review requirement

All 400 future shifted variants require human semantic-preservation and boundary review before evaluation. C1, C2, and C3 also require acceptable naturalness. Allowed outcomes are `ACCEPT`, `REWRITE_REQUIRED`, and `REJECT`; rewritten items are reviewed again.

The future review table records challenge/seed identity, condition, canonical label, semantic preservation, naturalness, boundary consistency, decision, and notes.

## 9. Evaluation-only policy

Challenge seeds and variants are prohibited from training and tuning. Repeated inspection while changing the same model invalidates a final result; subsequent evaluations must be labelled exploratory. Final reporting requires a frozen model/configuration and a frozen challenge benchmark.

## 10. Metrics

Primary outcomes:

- macro-F1 per condition; and
- macro-F1 change from matched C0.

Secondary outcomes:

- accuracy;
- per-class precision, recall, and F1;
- paired prediction consistency;
- robustness flip rate; and
- optional recovery rate.

No metrics or statistical-significance results were calculated in this task.

## 11. What this benchmark does NOT test

The main benchmark excludes OOD/unrelated services, adversarial attacks, prompt injection, privacy/redaction, calibration, conformal prediction, unknown-intent detection, and an ambiguity/clarification diagnostic set. `CLARIFY_REQUIRED` remains an evaluation annotation state and is not a sixth challenge class.

## 12. Limitations

These are controlled robustness conditions and must not be described as representative of all real Bangladeshi citizen language variation. The panel will be small and balanced by design. Script profile is not language identity, generated or assisted variants can carry authoring bias, and targeted human review is not population sampling. Generation provenance must be disclosed item by item.

## 13. Freeze status

**SCHEMA_FROZEN_V1**

Frozen now:

- benchmark identity and five labels;
- target size and matched conditions;
- TEST-only family-clean eligibility;
- deterministic coverage and tie-breaking rules;
- semantic preservation and rejection rules;
- human review and provenance fields;
- leakage/tuning prohibitions; and
- planned metrics.

Not created:

- final seed IDs or `challenge_seed_panel_v1.csv`;
- transformed query text;
- challenge predictions or metrics; and
- any model, dataset split, or training change.
