# Historical Five-Class Baseline Provenance

## Finding

**Overall provenance: UNVERIFIED.**

The remembered research target is internally consistent with a real artifact: both `NID Query Datasheet` and `Copy of NID Query Datasheet` contain exactly 1,454 NID queries and exactly five coarse string labels. However, no code, configuration, split manifest, model metadata, predictions, confusion matrix, or metrics file in the repository establishes how the remembered 96.36% IID Macro F1 or 82.64% shifted Macro F1 was produced.

## Dataset identity

**Verdict: LIKELY historical authoritative source, not confirmed training input.**

Evidence:

1. Both native Google Sheets contain 1,454 rows.
2. Their CSV exports are byte-identical (`SHA-256 6de6ba4f...e7faa`).
3. Their five `problem` labels exactly match the legacy keys in `taxonomy/nid.yaml::source_dataset_mapping`.
4. Repository audits explicitly refer to a previously discussed 1,454-row sheet.
5. Against confirmation: the sheet was absent when the repository corpus builder ran, and no loader/config/history points to either Drive file.

The `source_type=REAL` value is self-declared metadata and was not independently verified. The two Sheets should be treated as one content version with two Drive objects until provenance/version history is reviewed.

## Exact five-class ontology

| String label | Rows | Modern taxonomy mapping (metadata only) |
|---|---:|---|
| `NID Information Correction` | 267 | `NID_CORRECTION` |
| `New NID Registration` | 448 | `NID_REGISTRATION` |
| `Lost/Stolen NID` | 236 | `NID_REPLACEMENT` |
| `NID Online Problem` | 305 | `NID_ONLINE_SERVICES` |
| `Smart ID Card` | 198 | `NID_SMART_CARD` |

The label field is `problem` and is string encoded. No five-class `label2id`, `id2label`, serialized encoder, or stable numeric mapping was found. The Sheet's `parent_id` is not a class ID; its block-like values are inconsistent with a 0-4 encoder.

## IID 96.36

**Verdict: UNVERIFIED.**

- Exact value not found in repository or relevant Drive search.
- No historical five-class evaluation script or prediction/result file found.
- Averaging mode cannot be independently confirmed beyond the remembered description “Macro F1.”
- Historical train/dev/test membership, random seed, and checkpoint are unknown.
- Modern six-service results cannot be substituted: they use different data, ontology, tasks, and routing.

## Shifted 82.64 and 13.72-point gap

**Verdict: UNVERIFIED.**

- Exact values not found in repository or relevant Drive search.
- No shifted/challenge NID file was found locally or linked by current code.
- “Distribution shift” cannot be resolved to Banglish, typos, paraphrases, human-authored examples, or another construction from available evidence.
- Sample count, source, independence, leakage risk, and metric code are unknown.
- The arithmetic reference is consistent: 96.36 - 82.64 = 13.72 percentage points, but arithmetic consistency is not experimental reproduction.

## Current model is a different baseline

The current repository trains Hugging Face `AutoModelForSequenceClassification` models from `xlm-roberta-base`, not a five-class NID-only classifier. Current data has six services, 49 parents, 264 intent leaves, and 73 NID intents. NID intent uses a service-level XLM-R head with parent-conditioned text/masking. The local selected NID intent metadata records 73 labels, 12 epochs, DEV accuracy 0.753425 and DEV Macro F1 0.697586. This is a later system and does not validate the historical scores.

Static default hyperparameters are seed 42, max length 128, batch 16 (or 8 in small intent configs), evaluation batch 32, learning rate 2e-5, weight decay 0.01, warmup 0.1, early stopping, and DEV Macro F1 checkpoint selection. Later repair configs use lower learning rates. The historical five-class hyperparameters are not recoverable from current evidence.

## Leakage and reproducibility warnings

1. The historical Sheet has seven duplicate normalized query groups. Without its historical split membership, cross-split duplicate leakage cannot be tested.
2. No historical split manifest or seed exists, so rerunning an assumed random split would not reproduce the original evaluation.
3. No shifted dataset exists in the audited project-local locations; its independence from the IID data cannot be assessed.
4. The taxonomy only supplies coarse-to-parent mappings, not row-level migration to 73 intents.
5. `nid_migration_review.csv` has zero rows; the current 876-row NID corpus is freshly synthetic/paraphrased rather than migrated from the 1,454-row source.
6. Modern augmented/repair training variants and duplicate backup filenames could be mistaken for historical inputs unless a run manifest is used.

## Required evidence for reproduction

Before the historical claims can be frozen, recover or reconstruct explicitly: the exact source revision, immutable export, label encoder, split membership/seed, preprocessing code, model/tokenizer/checkpoint, IID prediction export, shifted dataset and construction protocol, and metric implementation. This audit does not infer any of them.
