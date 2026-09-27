# Phase 0 Task 3 — Canonical Five-Class Baseline Result

## Experiment identity

- Experiment: `EXP-P0-BASELINE-001`
- Protocol: `NID-5CLASS-PHASE0-V1`
- Model: `TFIDF-LOGREG-V1`
- Seed: `42`
- Starting Git commit: `908edc5d20321375fe572f6dc7c7b8fab85a2333`
- Source raw SHA-256: `6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa`
- Split-manifest SHA-256: `4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1`
- Fixed-config SHA-256: `a7546377637df41f5ebe353a717ccd6a9b779197ab3829e7c726aa51a773c315`

This run used the 1,017 TRAIN rows to fit both the TF-IDF vocabulary and
logistic-regression classifier. DEV (219 rows) and TEST (218 rows) were
transform-only. The fixed classifier was evaluated on TEST once, after the
DEV artifacts were written. No search, tuning, augmentation, relabeling, or
split modification occurred.

## Frozen baseline

The word-level TF-IDF vectorizer used unigrams and bigrams, no lowercasing,
sublinear term frequency, L2 normalization, and the frozen minimal Unicode
normalization. The balanced logistic-regression classifier used `C=1.0`, the
`lbfgs` solver, `max_iter=2000`, and `random_state=42`.

- TF-IDF features: 3,393
- Fit time: 3.841841 seconds
- Converged: yes
- Optimizer iterations: 30
- Python: 3.13.9
- scikit-learn: 1.9.0
- NumPy: 2.5.1

No fitted vectorizer or model binary was serialized. Reproducibility comes
from the private source freeze, committed split manifest, fixed config,
runner, and package-version record.

## DEV result

- Accuracy: 0.936073
- Macro precision: 0.941029
- Macro recall: 0.935876
- Macro-F1: 0.937334
- Errors: 14 / 219

| Label | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| NID Information Correction | 0.883721 | 0.950000 | 0.915663 | 40 |
| New NID Registration | 0.914286 | 0.955224 | 0.934307 | 67 |
| Lost/Stolen NID | 0.939394 | 0.861111 | 0.898551 | 36 |
| NID Online Problem | 1.000000 | 0.913043 | 0.954545 | 46 |
| Smart ID Card | 0.967742 | 1.000000 | 0.983607 | 30 |

Confusion matrix (rows are true labels and columns are predicted labels in
frozen ID order 0–4):

```text
[[38, 2, 0, 0, 0],
 [ 1,64, 1, 0, 1],
 [ 3, 2,31, 0, 0],
 [ 1, 2, 1,42, 0],
 [ 0, 0, 0, 0,30]]
```

## TEST result

- Accuracy: 0.922018
- Macro precision: 0.918029
- Macro recall: 0.924760
- Macro-F1: 0.920171
- Errors: 17 / 218

| Label | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| NID Information Correction | 0.904762 | 0.950000 | 0.926829 | 40 |
| New NID Registration | 0.924242 | 0.910448 | 0.917293 | 67 |
| Lost/Stolen NID | 0.878788 | 0.828571 | 0.852941 | 35 |
| NID Online Problem | 1.000000 | 0.934783 | 0.966292 | 46 |
| Smart ID Card | 0.882353 | 1.000000 | 0.937500 | 30 |

Confusion matrix (same frozen label order):

```text
[[38, 2, 0, 0, 0],
 [ 0,61, 4, 0, 2],
 [ 3, 1,29, 0, 2],
 [ 1, 2, 0,43, 0],
 [ 0, 0, 0, 0,30]]
```

## Historical-reference interpretation

The remembered IID Macro-F1 of 96.36% remains an **UNVERIFIED historical
reference**. Its split, model, and preprocessing artifacts were not
recovered. The historical result therefore is not a valid direct reproduction
target for this run.

The historical 96.36% result could not be independently reproduced because
its split/model artifacts were unavailable. `TFIDF-LOGREG-V1` establishes the
first reproducible baseline under the newly frozen Phase 0 protocol. It is not
valid to calculate or interpret a performance difference between these two
results as though they came from equivalent experiments.

The remembered shifted Macro-F1 of 82.64% also remains **UNVERIFIED**. No
shift experiment was performed in this task, and no replacement shift set was
created. Canonical distribution-shift challenge sets remain deferred to
Phase 1.

## Aggregate error record

No raw query appears in committed evaluation artifacts. The aggregate error
summary records confusion counts, class totals, and conflict group IDs only.
One DEV error and one TEST error involved their split's known conflicting-label
duplicate group. The two known conflict groups remained confined to their
assigned split throughout evaluation; no labels were repaired.

## Reproduction command

From the repository root, with the private frozen source at its documented
default path:

```bat
"D:\Files\Academic\4-1\NLP\nlp\Scripts\python.exe" research\phase0\run_nid_5class_baseline.py
```

This command performs the complete fixed run, including its one final TEST
evaluation. Future development must not alter this recorded result through
TEST-driven tuning.
