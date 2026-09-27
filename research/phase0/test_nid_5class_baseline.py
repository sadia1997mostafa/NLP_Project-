"""Small reproducibility checks for the frozen Phase 0 NID baseline."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from research.phase0.run_nid_5class_baseline import (
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_SPLITS,
    PREDICTION_COLUMNS,
    fit_baseline,
    load_and_validate,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[2]
PHASE0 = ROOT / "research/phase0"
RESULTS = PHASE0 / "results"


def frozen_records():
    return load_and_validate(
        ROOT.parent
        / f"{ROOT.name}_private"
        / "phase0/nid_5class_source_v1.csv",
        PHASE0 / "nid_5class_split_manifest_v1.csv",
        PHASE0 / "nid_5class_labels_v1.json",
        PHASE0 / "nid_5class_source_manifest_v1.json",
    )


def test_frozen_manifest_and_split_contract():
    manifest = PHASE0 / "nid_5class_split_manifest_v1.csv"
    assert sha256_file(manifest) == EXPECTED_MANIFEST_SHA256
    records, labels, _ = frozen_records()
    assert len(labels) == 5
    assert {split: sum(row["split"] == split for row in records) for split in EXPECTED_SPLITS} == EXPECTED_SPLITS
    group_splits = {}
    for row in records:
        group_splits.setdefault(row["normalized_text_sha256"], set()).add(row["split"])
    assert all(len(splits) == 1 for splits in group_splits.values())


def test_fit_rejects_non_train_rows_and_is_dev_deterministic():
    records, _, _ = frozen_records()
    config = yaml.safe_load(
        (PHASE0 / "nid_5class_baseline_tfidf_logreg_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    train = [row for row in records if row["split"] == "train"]
    dev = [row for row in records if row["split"] == "dev"]
    vectorizer_a, model_a, _ = fit_baseline(train, config)
    vectorizer_b, model_b, _ = fit_baseline(train, config)
    assert model_a.predict(vectorizer_a.transform([row["normalized_text"] for row in dev])).tolist() == model_b.predict(vectorizer_b.transform([row["normalized_text"] for row in dev])).tolist()
    try:
        fit_baseline(train + dev[:1], config)
    except ValueError as error:
        assert "TRAIN rows only" in str(error)
    else:
        raise AssertionError("fit_baseline accepted a DEV row")


def test_result_schema_and_no_raw_text():
    for split, count in (("dev", 219), ("test", 218)):
        metrics = json.loads(
            (RESULTS / f"tfidf_logreg_v1_{split}_metrics.json").read_text(
                encoding="utf-8"
            )
        )
        assert metrics["rows"] == count
        assert len(metrics["per_class"]) == 5
        assert len(metrics["confusion_matrix"]) == 5
        assert all(len(row) == 5 for row in metrics["confusion_matrix"])
        with (
            RESULTS / f"tfidf_logreg_v1_{split}_predictions.csv"
        ).open("r", encoding="utf-8", newline="") as handle:
            predictions = list(csv.DictReader(handle))
        assert len(predictions) == count
        assert list(predictions[0]) == PREDICTION_COLUMNS
        assert "text" not in predictions[0]
