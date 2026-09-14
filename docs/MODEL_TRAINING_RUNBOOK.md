# Prothom Model Training Runbook

The repository is prepared for the next phase, but no model has been trained.
Run all commands from the repository root with the project virtual environment.

## Preparation gate

```bat
python src\preprocessing\validate_label_contract.py
python src\preprocessing\validate_pretraining_data.py
python -m unittest discover -s tests -v
python -m compileall src
```

Install the optional training dependencies from `requirements-training.txt` before loading the configured backbone. The initial configuration in `configs/classifier_base.yaml` uses `xlm-roberta-base`; its hyperparameters are starting points, not optimized values.

The training entry point defaults to a dry run. This validates the config and label map without loading a model:

```bat
python -m src.models.train_classifier --task service
```

## First baseline runs (future work)

These commands explicitly cross the training boundary and must only be run after owner review:

```bat
python -m src.models.train_classifier --task service --execute-training
python -m src.models.train_classifier --task parent --execute-training
python -m src.models.train_classifier --task intent --execute-training
python -m src.models.train_classifier --task priority --execute-training
```

Each task reads `data/splits/train.csv` and `data/splits/dev.csv`, uses its frozen map under `contracts/label_maps/`, and writes only to `models/checkpoints/<task>`. Complete query families remain in one split.

For priority imbalance, set `class_weighting: "balanced"` in the config to enable inverse-frequency weighted cross-entropy. It is disabled initially; do not synthesize High-priority rows solely for balance.

## Evaluation

After a future prediction export containing `gold_label,predicted_label`:

```bat
python -m src.models.evaluate_classifier path\to\predictions.csv --output path\to\metrics.json
```

Reported classification metrics are accuracy, macro precision, macro recall, macro F1, weighted F1, and confusion matrix. OOD helpers support AUROC, AUPR, and FPR95 once calibrated model scores exist.

## Confidence and OOD

`src/models/inference.py` exposes label confidence, top-k alternatives, and a max-softmax-derived OOD score. Both confidence and OOD thresholds are `null` in the initial config because they require calibration on held-out in-domain and OOD data. Do not treat the baseline score as calibrated.

`predict_understanding()` intentionally raises an error until trained predictors are injected. It never emits fabricated predictions.

## Dependency note

The current preparation environment has pandas, PyYAML, NumPy, and scikit-learn. PyTorch and Transformers were intentionally not downloaded during preparation. Install them from `requirements-training.txt` only when the model-training phase begins.
