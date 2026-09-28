"""Validate the Phase 1 five-class intent contract and immutable inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from itertools import combinations
from pathlib import Path

import yaml


LABELS = {
    0: "NID Information Correction",
    1: "New NID Registration",
    2: "Lost/Stolen NID",
    3: "NID Online Problem",
    4: "Smart ID Card",
}
EXPECTED_LABEL_HASH = "ce54be5d44b78b1d1233a438f051089c9c86fe41f47f50bd637f9b8d083216fc"
EXPECTED_FAMILY_HASH = "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c"
UNSAFE_RAW_FIELDS = {"text", "text_a", "text_b", "query", "query_text", "raw_text"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_contract(root: Path, contract_path: Path, matrix_path: Path, conflicts_path: Path) -> dict[str, int | str]:
    labels_path = root / "research" / "phase0" / "nid_5class_labels_v1.json"
    manifest_path = root / "research" / "phase0" / "nid_5class_split_manifest_v1.csv"
    family_path = root / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv"
    family_manifest_path = root / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_manifest_v1.json"

    if sha256(labels_path) != EXPECTED_LABEL_HASH:
        raise ValueError("Immutable Phase 0 label hash changed")
    if sha256(family_path) != EXPECTED_FAMILY_HASH:
        raise ValueError("Frozen paraphrase-family map hash changed")
    family_manifest = json.loads(family_manifest_path.read_text(encoding="utf-8"))
    if family_manifest["family_map_sha256"] != EXPECTED_FAMILY_HASH:
        raise ValueError("Family-map manifest does not match the frozen map")

    frozen = json.loads(labels_path.read_text(encoding="utf-8"))
    frozen_rows = frozen["labels"]
    if {int(row["label_id"]): row["label_name"] for row in frozen_rows} != LABELS:
        raise ValueError("Frozen label IDs or names changed")

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    definitions = contract.get("labels", [])
    if len(definitions) != 5:
        raise ValueError("Contract must contain exactly five definitions")
    by_id = {int(row["label_id"]): row for row in definitions}
    if set(by_id) != set(LABELS):
        raise ValueError("Contract label IDs must be exactly 0-4")
    for label_id, label_name in LABELS.items():
        row = by_id[label_id]
        if row.get("label_name") != label_name:
            raise ValueError(f"Frozen label name mismatch for ID {label_id}")
        for field in ("short_definition", "include_when", "exclude_when", "clarification_triggers"):
            if not row.get(field):
                raise ValueError(f"Label {label_id} has empty {field}")
        for neighbor in row.get("confusing_neighbors", []):
            neighbor_id = int(neighbor["label_id"])
            if neighbor_id not in LABELS or neighbor_id == label_id:
                raise ValueError(f"Invalid confusing neighbor for label {label_id}")

    matrix_rows = read_csv(matrix_path)
    if len(matrix_rows) != 10:
        raise ValueError("Neighbor matrix must contain all ten unordered pairs")
    expected_pairs = {frozenset((a, b)) for a, b in combinations(LABELS.values(), 2)}
    actual_pairs = {frozenset((row["label_a"], row["label_b"])) for row in matrix_rows}
    if actual_pairs != expected_pairs:
        raise ValueError("Neighbor matrix pair inventory is incomplete or duplicated")
    if any(row["confusion_risk"] not in {"LOW", "MODERATE", "HIGH"} for row in matrix_rows):
        raise ValueError("Invalid confusion risk")

    manifest_rows = read_csv(manifest_path)
    valid_samples = {row["sample_id"] for row in manifest_rows}
    conflict_rows = read_csv(conflicts_path)
    if not conflict_rows:
        raise ValueError("Source conflict register is unexpectedly empty")
    with conflicts_path.open("r", encoding="utf-8-sig", newline="") as handle:
        fields = set(csv.DictReader(handle).fieldnames or [])
    if fields & UNSAFE_RAW_FIELDS:
        raise ValueError("Raw-text field found in Git-safe conflict register")
    for row in conflict_rows:
        if row["sample_id_a"] not in valid_samples or row["sample_id_b"] not in valid_samples:
            raise ValueError("Conflict register references an unknown sample ID")
        if row["label_a"] not in LABELS.values() or row["label_b"] not in LABELS.values():
            raise ValueError("Conflict register references an unknown label")

    return {
        "labels": len(definitions),
        "neighbor_pairs": len(matrix_rows),
        "conflicts": len(conflict_rows),
        "samples": len(manifest_rows),
        "status": contract["status"],
    }


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    base = root / "research" / "phase1" / "ontology"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=base / "nid_5class_intent_contract_v1.yaml")
    parser.add_argument("--matrix", type=Path, default=base / "nid_5class_confusing_neighbor_matrix_v1.csv")
    parser.add_argument("--conflicts", type=Path, default=base / "nid_5class_source_conflicts_v1.csv")
    args = parser.parse_args()
    result = validate_contract(root, args.contract, args.matrix, args.conflicts)
    print("INTENT CONTRACT VALIDATION: PASS")
    print(f"LABELS: {result['labels']}")
    print(f"PAIRWISE BOUNDARIES: {result['neighbor_pairs']}")
    print(f"SOURCE CONFLICTS: {result['conflicts']}")
    print(f"STATUS: {result['status']}")


if __name__ == "__main__":
    main()
