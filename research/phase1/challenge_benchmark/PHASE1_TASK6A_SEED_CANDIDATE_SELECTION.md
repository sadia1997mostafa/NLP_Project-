# Phase 1 Task 6A — Deterministic Challenge Seed Candidate Selection

## 1. Objective

This task executes the frozen `NID5-SHIFT-V1` structural selection protocol to produce 100 candidate semantic seeds and a complete deterministic reserve ordering. The candidates are not the final benchmark panel: every candidate remains subject to direct human review for classifiability, explicitness, and transformability.

Status: **CANDIDATES_SELECTED**. Final seed status: **NOT_FROZEN**.

## 2. Frozen dependencies

Selection verified and consumed the immutable Phase 0 source and split, the final Phase 1 paraphrase-family map, the `FROZEN_V1` five-class ontology, the source-conflict register, and the `SCHEMA_FROZEN_V1` challenge protocol. Model predictions, confidence values, and correctness were not inspected or used.

Key dependency hashes:

- Phase 0 source: `6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa`
- Phase 0 split: `4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1`
- Final family map: `2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c`
- Ontology manifest: `41dc39210d6ea603995788d4ddb0bfe8de4ca3a6c4aff62cf13d379c15ba1742`
- Challenge protocol manifest: `5516d8ae9d9e83d29fb8b0d08ff1a440efd41769e35666d58d1b17c3991e0326`

## 3. Eligible pool reconstruction

The selector reconstructed the eligible TEST-only family units from frozen inputs. Counts exactly matched the Task 5 profile:

| Label | Eligible family units |
|---|---:|
| NID Information Correction | 38 |
| New NID Registration | 65 |
| Lost/Stolen NID | 34 |
| NID Online Problem | 44 |
| Smart ID Card | 28 |
| **Total** | **209** |

Families touching TRAIN or DEV and known source-conflict samples were excluded before selection. Each eligible family contributes one deterministic representative, chosen by stable selection hash where a TEST-only family contains multiple eligible rows.

## 4. Deterministic selection algorithm

For each frozen label independently, the selector:

1. computes the frozen script profile and within-label length tertile;
2. groups family representatives into joint `(script_profile, length_band)` strata;
3. orders each stratum by `SHA256("NID5-SHIFT-V1|SEED-V1|" + sample_id)` and sample ID;
4. repeatedly takes the head of the least-filled available joint stratum, ordered by joint selection count, frozen script category, frozen length category, and stable hash;
5. takes the first 20 rows as candidates; and
6. continues the identical traversal to freeze the within-label reserve order.

No random number generator, Python `hash()`, model output, or manual example preference is involved.

## 5. Candidate panel

The Git-safe candidate table contains:

- 100 rows;
- exactly 20 rows per frozen label;
- 100 unique sample IDs;
- 100 unique paraphrase families; and
- `PENDING_HUMAN_REVIEW` status for every candidate.

It contains no raw query text and is deliberately named `challenge_seed_candidates_v1.csv`, not `challenge_seed_panel_v1.csv`.

## 6. Coverage

Overall script-profile coverage:

| Script profile | Candidates |
|---|---:|
| BENGALI_SCRIPT_DOMINANT | 20 |
| LATIN_SCRIPT_DOMINANT | 42 |
| MIXED_SCRIPT | 38 |

Overall length-band coverage:

| Length band | Candidates |
|---|---:|
| SHORT | 35 |
| MEDIUM | 32 |
| LONG | 33 |

The script distribution reflects frozen pool availability. In particular, the Smart ID Card eligible pool has no Bengali-script-dominant family representative; the protocol does not fabricate an unavailable stratum.

## 7. Reserve ordering

The remaining 109 eligible family units are stored in a deterministic reserve order. If human review rejects a candidate, a later task must take replacements from this pre-frozen ordering within the affected label. Manual cherry-picking or selecting a replacement based on model behavior is prohibited.

No replacements were made in this task.

## 8. Leakage checks

- Candidates from Phase 0 TEST only: PASS
- Candidate family overlap with TRAIN: 0
- Candidate family overlap with DEV: 0
- Known source-conflict candidates: 0
- Duplicate candidate sample IDs: 0
- Duplicate candidate families: 0
- Model outputs used: NO

## 9. Human semantic review

Structural selection cannot decide whether raw text is unambiguously classifiable under `FROZEN_V1`, explicit enough to preserve the requested action, or suitable for all four meaning-preserving transformations. A private 100-row review queue therefore records the raw query text and leaves every semantic-review field blank.

The interactive tool derives `ACCEPT` only when the human answers YES to all three checks. Any NO derives `REJECT`. It saves after each confirmation and safely resumes without overwriting completed decisions. Codex made no review decisions.

## 10. Freeze status

Candidate selection status: **CANDIDATES_SELECTED**.

Final seed status: **FINAL_SEED_PANEL_NOT_FROZEN**.

Not created or performed:

- `challenge_seed_panel_v1.csv`;
- final challenge IDs;
- C0 benchmark rows;
- C1–C4 transformations;
- model training or evaluation; or
- rejected-candidate replacement.
