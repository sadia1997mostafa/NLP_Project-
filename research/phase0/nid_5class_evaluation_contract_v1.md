# NID Five-Class Evaluation Contract v1

## Historical remembered evaluation

- IID Macro-F1: **96.36%**
- Shift Macro-F1: **82.64%**
- Shift gap: **13.72 percentage points**
- Status: **UNVERIFIED HISTORICAL REFERENCE**

These values have not been reproduced. Their original split, model, checkpoint,
predictions, metric implementation and shifted dataset were not recovered.

## New canonical Phase 0 IID evaluation

Protocol: `NID-5CLASS-PHASE0-V1`

- Training: rows where manifest `split == train`
- Model selection and tuning: rows where manifest `split == dev`
- Final IID evaluation: rows where manifest `split == test`
- Primary metric: Macro-F1
- Secondary metrics: accuracy, macro precision, macro recall, per-class
  precision/recall/F1, and confusion matrix

The TEST split must not be used for model selection, hyperparameter tuning,
threshold tuning, data editing, label revision, or split revision.

## Distribution-shift evaluation

Historical shifted dataset: **NOT RECOVERED**.

No replacement shift set is invented in Phase 0. Canonical distribution-shift
challenge sets will be constructed and frozen during Phase 1.

The remembered 82.64% score must not be compared directly with the new
canonical IID test result as though both used the same evaluation protocol.
