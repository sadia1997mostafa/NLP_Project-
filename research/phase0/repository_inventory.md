# Phase 0 Repository Inventory

## Repository state

- Root: `D:\Files\Academic\4-1\NLP\NLP Project\NLP_Project-`
- Repository name: `NLP_Project-`
- Branch: `feature/ui-professional-refresh`
- HEAD: `bada1269e18688d35080608d974bd03513a59e1e`
- Remote: `origin = https://github.com/sadia1997mostafa/NLP_Project-.git`
- The worktree was already dirty. This audit did not restore, stage, delete, or overwrite any pre-existing change.

Pre-existing modified areas include the app server/UI, `src/models/inference.py`, and intent evaluation outputs. Pre-existing untracked areas include a duplicate JavaScript file, generated NLU augmentation data/report, intent TEST outputs, evaluation backups/logs, and a duplicate training script. The exact status is recorded in `phase0_task1_summary.json`.

## Concise functional inventory

| Area | Important paths | Current role |
|---|---|---|
| Historical NID source | `G:\My Drive\NID Query Datasheet.gsheet`; `Copy of NID Query Datasheet.gsheet` | Two content-identical native Sheets with 1,454 rows and five coarse labels; outside Git |
| Frozen taxonomy/contracts | `taxonomy/`; `contracts/labels.yaml`; `contracts/label_maps/` | Six services, 49 parents, 264 fine-grained query topics |
| Annotation inputs | `data/annotations/` | Birth, passport, tax, police GD, and driving-licence pilot/expanded assets |
| Canonical data | `data/processed/` | Six-service synthetic/paraphrased canonical corpus and reports |
| Stored splits | `data/splits/train.csv`, `dev.csv`, `test.csv`, `ood_*.csv` | Family-aware model inputs; later augmented/repair variants also exist |
| Data preparation | `src/preprocessing/prepare_pretraining_data.py`; validators beside it | Corpus construction, normalization, splitting, integrity validation |
| Model input | `src/preprocessing/task_views.py`; `src/models/dataset.py` | Task projection, routing context, tokenization, label masks |
| Training | `src/models/train_classifier.py`; `configs/classifier_*.yaml` | XLM-R sequence classifiers; training is explicitly opt-in |
| Evaluation | `src/models/evaluate_*.py`; `models/evaluation/` | DEV/TEST predictions, metrics, OOD calibration, manifests, backups |
| Runtime | `src/models/inference.py`; `src/models/hierarchy.py`; `src/models/service_anchors.py` | Hierarchical service -> parent -> intent inference and confidence/OOD |
| Binary models | `models/final/`; `models/checkpoints/` | Local Git-ignored XLM-R weights and selection metadata |
| Backend/UI | `app/server.py`; `app/static/`; `scripts/start_local_app.ps1` | FastAPI showcase and browser UI |
| Privacy/retrieval/response | `src/privacy/`; `src/retrieval/`; `src/response/`; `knowledge_base/` | Integrated later-stage privacy-safe guidance application |
| Tests | `tests/` | Pretraining, response, privacy, integration, and UI checks |

Repository file counts excluding Git/model-weight directories: 65 CSV, 89 Python, 56 JSON, 16 YAML, 39 Markdown, and no local XLS/XLSX/IPYNB files.

## Historical-result search

The exact strings `96.36`, `82.64`, and `13.72` were not found in repository code, configs, documentation, or saved evaluation summaries. The following meaningful historical-source references were found:

| Location | Type | Meaning |
|---|---|---|
| `data/processed/NID_SOURCE_DATA_INVENTORY.md:3-14` | Generated documentation | Records that the 1,454-row source was absent when the canonical corpus was built |
| `src/preprocessing/prepare_pretraining_data.py:173-209` | Executable source | Searches only repository `data/` for a historical NID source; emits an empty migration review when absent |
| `taxonomy/nid.yaml:1282-1292` | Taxonomy metadata | Maps the five coarse source labels to five modern parent topics; it is not a row-level migration |
| `taxonomy/NID_COVERAGE_AUDIT.md:9-18` | Manually authored audit | Treats the five coarse labels as legacy coverage to be refined, not as the final ontology |
| `models/evaluation/*.json` and `docs/PROTHOM_FINAL_RESULTS.md` | Generated/current results | Report later six-service XLM-R results; they do not reproduce the remembered five-class scores |

`macro_f1` and `f1_score` occur throughout the modern XLM-R evaluation implementation. Those occurrences are current executable/generated evidence, not evidence for the historical 96.36/82.64 claims.

## Current preprocessing path

```text
CSV text
  -> pandas read_csv(dtype=str, keep_default_na=False, UTF-8-SIG)
  -> optional service filter
  -> optional parent filter
  -> select id, parent_query_id, text, task label
  -> Unicode NFC normalization
  -> collapse whitespace and strip ends
  -> for service-level intent only: prepend [SERVICE=...] [PARENT=...]
  -> AutoTokenizer for xlm-roberta-base/local equivalent
  -> truncate to max_length=128
  -> pad to max_length
  -> integer label from deterministic frozen contract map
  -> for service-level intent: attach parent-valid Boolean label mask
```

Responsible code:

- Normalization: `src/preprocessing/text_normalization.py::normalize_text`
- Task projection/context: `src/preprocessing/task_views.py::project_task`
- Context format and label order: `src/models/hierarchy.py`
- Tokenization: `src/models/dataset.py::EncodedTextDataset.__getitem__`
- Training/model construction: `src/models/train_classifier.py`

No lowercasing, punctuation stripping, number removal, URL replacement, Bangla transliteration, stopword removal, or destructive Bangla normalization occurs. Case folding is used only for duplicate/leakage keys. Training and evaluation load the same task-view/dataset functions. Dataset construction and later TRAIN-only augmentation are separate preprocessing stages and must not be confused with runtime text normalization.

## Current split path

`src/preprocessing/prepare_pretraining_data.py::build_splits` groups each query topic into four sorted `parent_query_id` families. F01/F02 go to train, F03 to dev, and F04 to test. This produces 1,584/792/792 rows (50/25/25). It is deterministic and family-stratified by construction; no random seed is involved. The stored splits have zero family overlap and zero exact normalized-text overlap across train/dev/test.

The historical 1,454-row Google Sheet has no split column or repository split manifest. Its historical IID split, seed, stratification, and shift/challenge construction remain unknown.

## Artifact classification

- Reproducible current inputs: tracked canonical CSVs, tracked train/dev/test CSVs, frozen label maps, configs.
- Reproducible current results: tracked evaluation JSON/CSV files whose producing scripts are present.
- Local runtime artifacts: Git-ignored `models/final/` and checkpoints; selection metadata is readable locally, weights were not loaded in this audit.
- Generated/untracked candidates: `train_nlu_augmented.csv`, augmentation report, TEST intent exports, backup evaluation directories/logs.
- Potentially confusing backups/duplicates: `src/models/train_classifier (1).py`, `app/static/main (1).js`, pre-augmentation/pre-repair evaluation folders.
- Historical source: native Google Sheets outside Git; both are identical at audit time, but neither is wired into current code.
