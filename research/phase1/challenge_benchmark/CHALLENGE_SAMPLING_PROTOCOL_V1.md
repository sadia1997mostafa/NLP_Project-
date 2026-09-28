# NID5-SHIFT-V1 Challenge Sampling Protocol

## 1. Objective

`NID5-SHIFT-V1` is an evaluation-only, matched robustness benchmark for the five frozen NID intent classes. It measures whether a fixed classifier preserves its decisions when the same citizen information need is expressed through realistic linguistic or surface-form shifts. It is not a training corpus, tuning set, OOD benchmark, or reconstruction of the unrecovered historical shifted evaluation.

## 2. Frozen dependencies

The protocol depends on, and may not modify:

- the 1,454-row `NID-5CLASS-PHASE0-V1` source and split;
- the Phase 0 TEST membership of 218 rows;
- the final Phase 1 paraphrase-family map;
- the five labels and `FROZEN_V1` ontology;
- the source-conflict register and human-frozen Smart Card boundaries.

Any dependency hash mismatch invalidates profiling or selection. No classifier output is an input to seed selection.

## 3. Evaluation population

The population is restricted to frozen Phase 0 TEST rows. The design uses the same 100 semantic seeds under five conditions, permitting paired comparisons across expression conditions while holding source intent constant.

The intended benchmark has 500 instances:

- 100 original controls;
- 100 natural paraphrases;
- 100 Banglish script-shift variants;
- 100 code-mixed variants; and
- 100 typo/noise variants.

Each frozen label contributes 20 seeds and therefore 100 matched instances.

## 4. Eligible seed definition

A candidate is eligible only if all of the following hold:

1. Its frozen Phase 0 split is TEST.
2. Its frozen label is one of IDs 0–4.
3. It exists exactly once in the final family map.
4. Its family contains no TRAIN member.
5. Its family contains no DEV member.
6. It is not one of the six historical source-conflict samples.
7. It is `CLASSIFIABLE` under `FROZEN_V1`, not `CLARIFY_REQUIRED`.
8. Its requested action and lifecycle context are explicit enough that a later variant can be judged for semantic preservation.
9. Eligibility does not rest on an isolated keyword.

The aggregate profile applies every deterministic structural rule and verifies a feasible margin in each class. Before final seed freeze, a human must confirm rules 7–9 for every proposed seed. A rejected candidate is skipped using the frozen deterministic ordering; its label is never changed.

## 5. Leakage exclusions

Challenge seeds must come from TEST-only families. A family touching TRAIN or DEV is excluded in full for seed eligibility. Known source-conflict samples are excluded even when the ontology now has a canonical future boundary, because their historical labels are inconsistent.

All generated variants inherit evaluation-only status and the seed family. Neither seeds nor variants may enter training, augmentation, model selection, threshold tuning, calibration, or prompt/model iteration informed by benchmark performance.

## 6. Target seed panel

The frozen target is exactly 100 seeds:

| Label ID | Label | Seeds |
|---:|---|---:|
| 0 | NID Information Correction | 20 |
| 1 | New NID Registration | 20 |
| 2 | Lost/Stolen NID | 20 |
| 3 | NID Online Problem | 20 |
| 4 | Smart ID Card | 20 |

At most one seed may be selected from a paraphrase family. This task does not select those seeds or create `challenge_seed_panel_v1.csv`.

## 7. Coverage strata

Selection is stratified by frozen label, surface-script profile, and within-label query-length band.

### Script profile

Count Bengali and ASCII-Latin alphabetic Unicode code points after the frozen minimal NFC/whitespace normalization:

- `BENGALI_SCRIPT_DOMINANT`: Bengali characters are at least 80% of counted Bengali+Latin alphabetic characters.
- `LATIN_SCRIPT_DOMINANT`: Latin characters are at least 80%.
- `MIXED_SCRIPT`: neither script reaches 80%, including the deterministic fallback when neither count is present.

This is a surface category. `LATIN_SCRIPT_DOMINANT` must not be reported as proof that a query is Banglish.

### Length band

Within each label's eligible pool, rank candidates by normalized Unicode code-point length. Divide ranked candidates into near-equal `SHORT`, `MEDIUM`, and `LONG` tertiles using `floor(rank * 3 / n)`. When lengths tie, order by the stable selection hash and then sample ID. A tie may cross a band boundary; the documented stable ordering resolves it reproducibly.

## 8. Deterministic selection algorithm

The future seed-freeze task must use this procedure without inspecting model predictions:

1. Revalidate all frozen dependency hashes.
2. Recompute the aggregate eligible pool and stop if any label has fewer than 20 eligible family units.
3. Within each label, compute script profile, length band, and stable tie key.
4. Create available joint strata `(script_profile, length_band)`.
5. Allocate the 20-label quota as evenly as availability permits across script profiles and length bands. No unavailable stratum is fabricated.
6. Traverse candidates within each stratum by:

   `SHA256("NID5-SHIFT-V1|SEED-V1|" + sample_id)`

7. Enforce one seed per family.
8. Present candidates in that deterministic order for human semantic eligibility review.
9. If a candidate is not classifiable, not sufficiently explicit, or cannot support meaning-preserving transformations, reject it and advance to the next ordered candidate in the same stratum. Do not relabel it.
10. If a stratum is exhausted, redistribute its unmet quota deterministically to the least-filled available strata, ordered by `(selected_count, script_profile, length_band)`.
11. Stop only when each label has exactly 20 accepted seeds. If any label cannot reach 20, fail rather than lower the quota.

Python's process-dependent `hash()` is prohibited. No seed selection is executed in this protocol-freeze task.

## 9. Challenge conditions

### C0 — ORIGINAL

The unchanged frozen source query. It is the matched control.

### C1 — NATURAL_PARAPHRASE

A natural reformulation with changed syntax, wording, question form, synonyms, or conversationality. It may not add circumstances or change action, object, lifecycle, or coarse intent.

### C2 — BANGLISH_SCRIPT_SHIFT

A plausible Bangladeshi Latin-script Banglish rendering of the same meaning. Transliteration need not be standardized and common English civic terms may remain English. Human review—not Latin script alone—determines whether it is plausible Banglish.

### C3 — CODE_MIXED

Natural Bengali-English or Banglish-English mixing that preserves the request. Artificial word-by-word alternation is rejected.

### C4 — TYPO_NOISE

One to three localized low-to-moderate spelling, whitespace, punctuation, phonetic, keyboard, repeated-character, or abbreviation perturbations where possible. The result must remain readable and semantically unambiguous.

## 10. Semantic-preservation contract

Every shifted variant must preserve:

- the canonical coarse label;
- requested citizen action;
- service lifecycle stage;
- critical entity relationships and polarity;
- first issuance versus replacement;
- authoritative-record correction versus portal operation; and
- Smart Card lifecycle boundaries frozen in `FROZEN_V1`.

Reject or rewrite a variant if it changes intent, becomes ambiguous, introduces unstated circumstances, removes decisive boundary information, creates a conflicting lifecycle, or is unnatural/unintelligible. A failed transformation is never repaired by changing its label.

## 11. Human review contract

Every shifted variant must receive human review before benchmark evaluation. The future review record contains:

- challenge ID and seed sample ID;
- condition;
- canonical label ID/name;
- `semantic_preserved`;
- `naturalness_acceptable`;
- `boundary_consistent`;
- `review_decision`; and
- human notes.

Allowed decisions are `ACCEPT`, `REWRITE_REQUIRED`, and `REJECT`. Acceptance always requires semantic preservation and boundary consistency. C1, C2, and C3 additionally require acceptable naturalness. Rewrites must be reviewed again.

## 12. Leakage and tuning policy

- Seeds are TEST-only and family-clean relative to TRAIN and DEV.
- Challenge variants are permanently evaluation-only.
- Text and results may not be used for training, augmentation, hyperparameter selection, threshold tuning, or iterative model repair.
- Repeated benchmark inspection while changing the same model is prohibited as final evaluation practice.
- A model changed after benchmark inspection produces an explicitly exploratory result.
- Final paper results require a frozen model/configuration evaluated against the frozen benchmark.

## 13. Planned metrics

Primary outcomes:

- macro-F1 for each C0–C4 condition; and
- macro-F1 delta relative to C0 on the same seeds.

Secondary outcomes:

- accuracy;
- per-class precision, recall, and F1;
- paired prediction consistency between each shifted form and C0;
- robustness flip rate: C0 correct and shifted prediction incorrect; and
- optional recovery rate: C0 incorrect and shifted prediction correct.

No metrics or significance tests are calculated in this task.

## 14. Excluded benchmark scopes

The main five-class macro-F1 benchmark excludes OOD and unrelated-service examples, adversarial attacks, prompt injection, privacy/redaction experiments, calibration or conformal sets, unknown-intent detection, and a separate ambiguous/clarification diagnostic set. `CLARIFY_REQUIRED` is not a sixth class.

## 15. Limitations

The five conditions are controlled robustness tests. They must not be described as a representative sample of all real Bangladeshi citizen language variation. The fixed 100-seed panel will support paired comparisons but cannot capture every dialect, device, literacy context, transliteration practice, or naturally occurring distribution shift. Generated or assisted variants require disclosed provenance and human review.

## Freeze statement

Protocol status: **SCHEMA_FROZEN_V1**. This task freezes schema, eligibility, sampling, review, leakage, provenance, and metric rules only. It selects no seeds and generates no challenge text.
