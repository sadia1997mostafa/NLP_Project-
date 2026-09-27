"""Verify the frozen Phase 0 artifacts without training or model inference."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE0 = Path(__file__).resolve().parent
RESULTS = PHASE0 / "results"
DEFAULT_PRIVATE_SOURCE = (
    ROOT.parent / f"{ROOT.name}_private" / "phase0" / "nid_5class_source_v1.csv"
)
EXPECTED_SOURCE_SHA256 = (
    "6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa"
)
EXPECTED_MANIFEST_SHA256 = (
    "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
)
EXPECTED_SPLITS = {"train": 1017, "dev": 219, "test": 218}
EXPECTED_LABELS = {
    "NID Information Correction": 267,
    "New NID Registration": 448,
    "Lost/Stolen NID": 236,
    "NID Online Problem": 305,
    "Smart ID Card": 198,
}
EXPECTED_METRICS = {
    "dev": {
        "accuracy": 0.9360730593607306,
        "macro_precision": 0.9410285038792165,
        "macro_recall": 0.935875693993799,
        "macro_f1": 0.937334391301132,
    },
    "test": {
        "accuracy": 0.9220183486238532,
        "macro_precision": 0.9180290297937358,
        "macro_recall": 0.9247603596922221,
        "macro_f1": 0.9201711625354878,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def compact_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_private_source(path: Path) -> tuple[list[str], list[list[str]]]:
    require(path.exists(), f"Private source missing: {path}")
    require(sha256_file(path) == EXPECTED_SOURCE_SHA256, "Private source SHA-256 mismatch")
    resolved = path.resolve()
    require(
        not resolved.is_relative_to(ROOT.resolve()),
        "Private source must be outside the Git repository",
    )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        rows = list(reader)
    require(len(rows) == 1454, f"Source rows changed: {len(rows)}")
    require("text" in header and "problem" in header, "Source schema changed")
    require(
        Counter(row[header.index("problem")] for row in rows)
        == Counter(EXPECTED_LABELS),
        "Source label inventory changed",
    )
    require(
        not (ROOT / "_private/phase0/nid_5class_source_v1.csv").exists(),
        "Old inside-repository private source still exists",
    )
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "_private/phase0/nid_5class_source_v1.csv"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(tracked.returncode != 0, "Private source is tracked by Git")
    return header, rows


def verify_split(header: list[str], source_rows: list[list[str]]) -> None:
    manifest_path = PHASE0 / "nid_5class_split_manifest_v1.csv"
    require(
        sha256_file(manifest_path) == EXPECTED_MANIFEST_SHA256,
        "Split manifest SHA-256 mismatch",
    )
    manifest = read_csv(manifest_path)
    require(len(manifest) == 1454, "Split manifest row count changed")
    require(
        Counter(row["split"] for row in manifest) == Counter(EXPECTED_SPLITS),
        "Split counts changed",
    )
    require(len({row["sample_id"] for row in manifest}) == 1454, "Sample IDs are not unique")
    require(
        {int(row["source_row_number"]) for row in manifest} == set(range(1, 1455)),
        "Not every source row is assigned exactly once",
    )
    text_index = header.index("text")
    for row in manifest:
        raw = source_rows[int(row["source_row_number"]) - 1]
        normalized_hash = hashlib.sha256(
            normalize_text(raw[text_index]).encode("utf-8")
        ).hexdigest()
        raw_hash = hashlib.sha256(compact_json_bytes(raw)).hexdigest()
        require(
            normalized_hash == row["normalized_text_sha256"],
            f"Normalized hash mismatch: {row['sample_id']}",
        )
        require(raw_hash == row["row_sha256"], f"Row hash mismatch: {row['sample_id']}")
    split_hashes = {
        split: {
            row["normalized_text_sha256"]
            for row in manifest
            if row["split"] == split
        }
        for split in EXPECTED_SPLITS
    }
    for left, right in (("train", "dev"), ("train", "test"), ("dev", "test")):
        require(
            not split_hashes[left].intersection(split_hashes[right]),
            f"{left}/{right} normalized-text overlap",
        )


def verify_results() -> None:
    for split, expected_rows in (("dev", 219), ("test", 218)):
        metrics = json.loads(
            (RESULTS / f"tfidf_logreg_v1_{split}_metrics.json").read_text(encoding="utf-8")
        )
        require(metrics["rows"] == expected_rows, f"{split} metric rows changed")
        for field, expected in EXPECTED_METRICS[split].items():
            require(metrics[field] == expected, f"Frozen {split} {field} changed")
        require(
            len(metrics["confusion_matrix"]) == 5
            and all(len(row) == 5 for row in metrics["confusion_matrix"]),
            f"{split} metrics confusion matrix is not 5x5",
        )
        predictions = read_csv(RESULTS / f"tfidf_logreg_v1_{split}_predictions.csv")
        require(len(predictions) == expected_rows, f"{split} prediction rows changed")
        require(
            "text" not in predictions[0] and "normalized_text" not in predictions[0],
            f"Raw text field found in {split} predictions",
        )
        confusion_rows = read_csv(
            RESULTS / f"tfidf_logreg_v1_{split}_confusion_matrix.csv"
        )
        require(
            len(confusion_rows) == 5 and all(len(row) == 6 for row in confusion_rows),
            f"{split} confusion CSV is not 5x5 plus row label",
        )
    run = json.loads((RESULTS / "tfidf_logreg_v1_run.json").read_text(encoding="utf-8"))
    require(run["test_evaluations"] == 1, "Official TEST evaluation count changed")
    json.loads((RESULTS / "tfidf_logreg_v1_error_summary.json").read_text(encoding="utf-8"))


def verify_artifact_manifest(path: Path) -> None:
    rows = read_csv(path)
    require(rows, "Artifact manifest is empty")
    for row in rows:
        artifact = (
            Path(row["relative_path"])
            if row["artifact_type"] == "EXTERNAL_PRIVATE"
            else ROOT / row["relative_path"]
        )
        require(artifact.exists(), f"Manifest artifact missing: {artifact}")
        require(
            artifact.stat().st_size == int(row["size_bytes"]),
            f"Manifest size mismatch: {artifact}",
        )
        require(sha256_file(artifact) == row["sha256"], f"Manifest hash mismatch: {artifact}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify frozen Phase 0 source, split, results, and artifact ledger without model execution."
    )
    parser.add_argument(
        "--private-source", type=Path, default=DEFAULT_PRIVATE_SOURCE,
        help="External private frozen CSV",
    )
    parser.add_argument(
        "--artifact-manifest", type=Path,
        default=PHASE0 / "phase0_artifact_manifest.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    header, source_rows = verify_private_source(args.private_source)
    verify_split(header, source_rows)
    verify_results()
    verify_artifact_manifest(args.artifact_manifest)
    print("PHASE 0 FREEZE VERIFICATION: PASS")
    print("SOURCE ROWS: 1454")
    print("SPLITS: train=1017 dev=219 test=218")
    print("OFFICIAL TEST EVALUATIONS: 1")
    print("PRIVATE SOURCE OUTSIDE GIT: PASS")


if __name__ == "__main__":
    main()
