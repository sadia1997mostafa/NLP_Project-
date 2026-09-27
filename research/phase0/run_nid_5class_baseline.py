"""Run the frozen Phase 0 five-class NID TF-IDF/logistic baseline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import time
import unicodedata
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import sklearn
import yaml
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SOURCE_SHA256 = (
    "6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa"
)
EXPECTED_MANIFEST_SHA256 = (
    "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
)
EXPECTED_ROWS = 1454
EXPECTED_SPLITS = {"train": 1017, "dev": 219, "test": 218}
PREDICTION_COLUMNS = [
    "sample_id",
    "true_label_id",
    "true_label_name",
    "predicted_label_id",
    "predicted_label_name",
    "correct",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def compact_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def normalize_text(value: object) -> str:
    """Apply only the frozen Phase 0 canonical normalization."""
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def read_private_source(path: Path) -> tuple[list[str], list[list[str]]]:
    if sha256_file(path) != EXPECTED_SOURCE_SHA256:
        raise ValueError("FROZEN SOURCE MISMATCH: raw SHA-256 changed")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        rows = list(reader)
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} source rows, found {len(rows)}")
    if "text" not in header or "problem" not in header:
        raise ValueError("Private source is missing text or problem")
    if any(len(row) != len(header) for row in rows):
        raise ValueError("Private source contains a row-width mismatch")
    return header, rows


def read_manifest(path: Path) -> list[dict[str, str]]:
    if sha256_file(path) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("FROZEN MANIFEST MISMATCH")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows


def load_and_validate(
    source_path: Path,
    manifest_path: Path,
    labels_path: Path,
    source_manifest_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    header, source_rows = read_private_source(source_path)
    manifest = read_manifest(manifest_path)
    labels_doc = json.loads(labels_path.read_text(encoding="utf-8"))
    source_doc = json.loads(source_manifest_path.read_text(encoding="utf-8"))

    labels = sorted(labels_doc["labels"], key=lambda item: int(item["label_id"]))
    if len(labels) != 5:
        raise ValueError(f"Expected five frozen labels, found {len(labels)}")
    label_to_id = {item["source_label"]: int(item["label_id"]) for item in labels}
    expected_counts = Counter(
        {item["source_label"]: int(item["sample_count"]) for item in labels}
    )
    text_index = header.index("text")
    label_index = header.index("problem")
    if Counter(row[label_index] for row in source_rows) != expected_counts:
        raise ValueError("Frozen source label counts changed")
    if source_doc["raw_file_sha256"] != EXPECTED_SOURCE_SHA256:
        raise ValueError("Source manifest raw hash differs from the protocol")

    required = {
        "sample_id",
        "source_row_number",
        "label_id",
        "label_name",
        "split",
        "group_id",
        "normalized_text_sha256",
        "row_sha256",
    }
    if len(manifest) != EXPECTED_ROWS or not required.issubset(manifest[0]):
        raise ValueError("Frozen split manifest schema or row count changed")
    if len({row["sample_id"] for row in manifest}) != EXPECTED_ROWS:
        raise ValueError("Sample IDs are not unique")
    source_numbers = [int(row["source_row_number"]) for row in manifest]
    if set(source_numbers) != set(range(1, EXPECTED_ROWS + 1)):
        raise ValueError("Every source row must be assigned exactly once")
    if Counter(row["split"] for row in manifest) != Counter(EXPECTED_SPLITS):
        raise ValueError("Frozen split sizes changed")

    records: list[dict[str, Any]] = []
    for manifest_row in manifest:
        source_row_number = int(manifest_row["source_row_number"])
        raw_cells = source_rows[source_row_number - 1]
        normalized = normalize_text(raw_cells[text_index])
        normalized_hash = sha256_bytes(normalized.encode("utf-8"))
        row_hash = sha256_bytes(compact_json_bytes(raw_cells))
        label_name = raw_cells[label_index]
        label_id = label_to_id.get(label_name)
        if normalized_hash != manifest_row["normalized_text_sha256"]:
            raise ValueError(f"Normalized hash changed for {manifest_row['sample_id']}")
        if row_hash != manifest_row["row_sha256"]:
            raise ValueError(f"Row hash changed for {manifest_row['sample_id']}")
        if label_id != int(manifest_row["label_id"]):
            raise ValueError(f"Label ID changed for {manifest_row['sample_id']}")
        if label_name != manifest_row["label_name"]:
            raise ValueError(f"Label name changed for {manifest_row['sample_id']}")
        records.append(
            {
                **manifest_row,
                "source_row_number": source_row_number,
                "label_id": label_id,
                "normalized_text": normalized,
            }
        )

    hashes_by_split = {
        split: {
            row["normalized_text_sha256"]
            for row in records
            if row["split"] == split
        }
        for split in EXPECTED_SPLITS
    }
    for left, right in (("train", "dev"), ("train", "test"), ("dev", "test")):
        if hashes_by_split[left] & hashes_by_split[right]:
            raise ValueError(f"Normalized-text leakage between {left} and {right}")
    return records, labels, source_doc


def build_estimator(config: dict[str, Any]) -> tuple[TfidfVectorizer, LogisticRegression]:
    vector_params = dict(config["vectorizer"]["parameters"])
    vector_params["ngram_range"] = tuple(vector_params["ngram_range"])
    classifier_params = dict(config["classifier"]["parameters"])
    return TfidfVectorizer(**vector_params), LogisticRegression(**classifier_params)


def fit_baseline(
    train_rows: list[dict[str, Any]], config: dict[str, Any]
) -> tuple[TfidfVectorizer, LogisticRegression, dict[str, Any]]:
    """Fit both components using only records explicitly assigned to TRAIN."""
    if not train_rows or {row["split"] for row in train_rows} != {"train"}:
        raise ValueError("fit_baseline accepts TRAIN rows only")
    vectorizer, classifier = build_estimator(config)
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        train_matrix = vectorizer.fit_transform(
            [row["normalized_text"] for row in train_rows]
        )
        classifier.fit(train_matrix, [row["label_id"] for row in train_rows])
    fit_seconds = time.perf_counter() - started
    convergence = [
        str(item.message)
        for item in captured
        if issubclass(item.category, ConvergenceWarning)
    ]
    metadata = {
        "fit_seconds": fit_seconds,
        "feature_count": len(vectorizer.get_feature_names_out()),
        "converged": not convergence,
        "convergence_warnings": convergence,
        "n_iter": classifier.n_iter_.astype(int).tolist(),
        "train_class_distribution": dict(
            sorted(Counter(row["label_name"] for row in train_rows).items())
        ),
    }
    return vectorizer, classifier, metadata


def evaluate_rows(
    rows: list[dict[str, Any]],
    vectorizer: TfidfVectorizer,
    classifier: LogisticRegression,
    labels: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[list[int]]]:
    """Transform-only evaluation; the vectorizer and classifier remain fixed."""
    label_ids = [int(item["label_id"]) for item in labels]
    id_to_name = {int(item["label_id"]): item["label_name"] for item in labels}
    matrix = vectorizer.transform([row["normalized_text"] for row in rows])
    truth = np.asarray([row["label_id"] for row in rows], dtype=int)
    predicted = classifier.predict(matrix).astype(int)
    precision, recall, f1, support = precision_recall_fscore_support(
        truth,
        predicted,
        labels=label_ids,
        zero_division=0,
    )
    macro_precision, macro_recall, macro_f1, _ = precision_recall_fscore_support(
        truth,
        predicted,
        labels=label_ids,
        average="macro",
        zero_division=0,
    )
    matrix_values = confusion_matrix(truth, predicted, labels=label_ids).tolist()
    metrics = {
        "rows": len(rows),
        "accuracy": float(accuracy_score(truth, predicted)),
        "macro_precision": float(macro_precision),
        "macro_recall": float(macro_recall),
        "macro_f1": float(macro_f1),
        "zero_division": 0,
        "label_order": label_ids,
        "per_class": [
            {
                "label_id": label_id,
                "label_name": id_to_name[label_id],
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index, label_id in enumerate(label_ids)
        ],
        "confusion_matrix": matrix_values,
    }
    predictions = [
        {
            "sample_id": row["sample_id"],
            "true_label_id": int(gold),
            "true_label_name": id_to_name[int(gold)],
            "predicted_label_id": int(prediction),
            "predicted_label_name": id_to_name[int(prediction)],
            "correct": bool(gold == prediction),
        }
        for row, gold, prediction in zip(rows, truth, predicted)
    ]
    return metrics, predictions, matrix_values


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_confusion(path: Path, matrix: list[list[int]], label_ids: list[int]) -> None:
    fields = ["true_label_id"] + [f"predicted_{label_id}" for label_id in label_ids]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for label_id, values in zip(label_ids, matrix):
            writer.writerow(
                {"true_label_id": label_id}
                | {f"predicted_{key}": value for key, value in zip(label_ids, values)}
            )


def confusion_pairs(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(
        (row["true_label_name"], row["predicted_label_name"])
        for row in predictions
        if not row["correct"]
    )
    return [
        {"true_label": gold, "predicted_label": pred, "count": count}
        for (gold, pred), count in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]


def split_error_summary(
    predictions: list[dict[str, Any]], records_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    errors = [row for row in predictions if not row["correct"]]
    return {
        "total_errors": len(errors),
        "confusion_pairs": confusion_pairs(predictions),
        "errors_per_true_class": dict(
            sorted(Counter(row["true_label_name"] for row in errors).items())
        ),
        "errors_per_predicted_class": dict(
            sorted(Counter(row["predicted_label_name"] for row in errors).items())
        ),
        "errors_in_duplicate_groups": sum(
            records_by_id[row["sample_id"]]["duplicate_group"] for row in errors
        ),
        "errors_in_conflicting_label_groups": sum(
            records_by_id[row["sample_id"]]["conflict_group"] for row in errors
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TFIDF-LOGREG-V1 on NID-5CLASS-PHASE0-V1."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "_private/phase0/nid_5class_source_v1.csv",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "research/phase0/nid_5class_split_manifest_v1.csv",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=ROOT / "research/phase0/nid_5class_labels_v1.json",
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=ROOT / "research/phase0/nid_5class_source_manifest_v1.json",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "research/phase0/nid_5class_baseline_tfidf_logreg_v1.yaml",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "research/phase0/results",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if config["protocol"] != "NID-5CLASS-PHASE0-V1":
        raise ValueError("Unexpected protocol in baseline config")
    if config["model_name"] != "TFIDF-LOGREG-V1":
        raise ValueError("Unexpected model name in baseline config")
    records, labels, source_doc = load_and_validate(
        args.source,
        args.manifest,
        args.labels,
        args.source_manifest,
    )
    split_rows = {
        split: [row for row in records if row["split"] == split]
        for split in EXPECTED_SPLITS
    }
    for split, expected in EXPECTED_SPLITS.items():
        if len(split_rows[split]) != expected:
            raise ValueError(f"{split} count changed")

    group_members = Counter(row["group_id"] for row in records)
    group_labels: dict[str, set[int]] = {}
    for row in records:
        group_labels.setdefault(row["group_id"], set()).add(row["label_id"])
    for row in records:
        row["duplicate_group"] = group_members[row["group_id"]] > 1
        row["conflict_group"] = len(group_labels[row["group_id"]]) > 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    vectorizer, classifier, fit_metadata = fit_baseline(split_rows["train"], config)
    label_ids = [int(item["label_id"]) for item in labels]

    # DEV is evaluated and frozen first. No estimator settings change afterward.
    dev_metrics, dev_predictions, dev_matrix = evaluate_rows(
        split_rows["dev"], vectorizer, classifier, labels
    )
    write_json(args.output_dir / "tfidf_logreg_v1_dev_metrics.json", dev_metrics)
    write_predictions(
        args.output_dir / "tfidf_logreg_v1_dev_predictions.csv", dev_predictions
    )
    write_confusion(
        args.output_dir / "tfidf_logreg_v1_dev_confusion_matrix.csv",
        dev_matrix,
        label_ids,
    )

    dev_frozen_at = datetime.now(timezone.utc).isoformat()

    # The frozen classifier is now evaluated on TEST once, without refitting.
    test_metrics, test_predictions, test_matrix = evaluate_rows(
        split_rows["test"], vectorizer, classifier, labels
    )
    write_json(args.output_dir / "tfidf_logreg_v1_test_metrics.json", test_metrics)
    write_predictions(
        args.output_dir / "tfidf_logreg_v1_test_predictions.csv", test_predictions
    )
    write_confusion(
        args.output_dir / "tfidf_logreg_v1_test_confusion_matrix.csv",
        test_matrix,
        label_ids,
    )

    records_by_id = {row["sample_id"]: row for row in records}
    conflict_groups = [
        {
            "group_id": group_id,
            "split": next(row["split"] for row in records if row["group_id"] == group_id),
        }
        for group_id, label_set in sorted(group_labels.items())
        if len(label_set) > 1
    ]
    error_summary = {
        "experiment_id": "EXP-P0-BASELINE-001",
        "dev": split_error_summary(dev_predictions, records_by_id),
        "test": split_error_summary(test_predictions, records_by_id),
        "known_label_conflict_groups": conflict_groups,
        "raw_query_text_included": False,
    }
    write_json(
        args.output_dir / "tfidf_logreg_v1_error_summary.json", error_summary
    )

    try:
        starting_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        starting_commit = "UNKNOWN"
    run_metadata = {
        "experiment_id": "EXP-P0-BASELINE-001",
        "protocol": "NID-5CLASS-PHASE0-V1",
        "model": "TFIDF-LOGREG-V1",
        "git_starting_commit": starting_commit,
        "source_raw_sha256": source_doc["raw_file_sha256"],
        "source_canonical_content_sha256": source_doc[
            "canonical_content_sha256"
        ],
        "split_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "config_sha256": sha256_file(args.config),
        "seed": int(config["seed"]),
        "package_versions": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "numpy": np.__version__,
        },
        "train_count": len(split_rows["train"]),
        "dev_count": len(split_rows["dev"]),
        "test_count": len(split_rows["test"]),
        "feature_count": fit_metadata["feature_count"],
        "fit_seconds": fit_metadata["fit_seconds"],
        "runtime_seconds": time.perf_counter() - started,
        "converged": fit_metadata["converged"],
        "convergence_warnings": fit_metadata["convergence_warnings"],
        "n_iter": fit_metadata["n_iter"],
        "train_class_distribution": fit_metadata["train_class_distribution"],
        "dev_outputs_frozen_at_utc": dev_frozen_at,
        "test_evaluations": 1,
        "test_evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_data_scope": "train_only",
        "dev_and_test_transform_only": True,
        "hyperparameter_search": False,
        "serialized_model_written": False,
    }
    write_json(args.output_dir / "tfidf_logreg_v1_run.json", run_metadata)

    print("INTEGRITY: PASS")
    print("TRAIN:", len(split_rows["train"]))
    print("DEV:", len(split_rows["dev"]))
    print("TEST:", len(split_rows["test"]))
    print("FEATURES:", fit_metadata["feature_count"])
    print("FIT SECONDS:", round(fit_metadata["fit_seconds"], 6))
    print("CONVERGED:", fit_metadata["converged"])
    print("N_ITER:", fit_metadata["n_iter"])
    print("DEV ACCURACY:", dev_metrics["accuracy"])
    print("DEV MACRO F1:", dev_metrics["macro_f1"])
    print("TEST ACCURACY:", test_metrics["accuracy"])
    print("TEST MACRO F1:", test_metrics["macro_f1"])
    print("OUTPUT:", args.output_dir)


if __name__ == "__main__":
    main()
