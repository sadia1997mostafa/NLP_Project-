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
EXPECTED_BOUNDARIES = {
    "NID5-ND-000048": (4, "Smart ID Card"),
    "NID5-ND-000050": (4, "Smart ID Card"),
    "NID5-ND-000071": (2, "Lost/Stolen NID"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_contract(
    root: Path,
    contract_path: Path,
    matrix_path: Path,
    conflicts_path: Path,
    decisions_path: Path | None = None,
) -> dict[str, int | str]:
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
    if contract.get("status") != "FROZEN_V1":
        raise ValueError("Intent contract is not frozen as FROZEN_V1")
    if contract.get("clarify_is_training_label") is not False:
        raise ValueError("CLARIFY_REQUIRED must remain evaluation-only")
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
    manifest_by_sample = {row["sample_id"]: row for row in manifest_rows}
    valid_samples = set(manifest_by_sample)
    decisions_path = decisions_path or contract_path.parent / "human_boundary_decisions_v1.csv"
    decision_rows = read_csv(decisions_path)
    if len(decision_rows) != 3 or {row["pair_id"] for row in decision_rows} != set(EXPECTED_BOUNDARIES):
        raise ValueError("Human boundary decision table must contain exactly the three targeted pairs")
    with decisions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        decision_fields = set(csv.DictReader(handle).fieldnames or [])
    if decision_fields & UNSAFE_RAW_FIELDS:
        raise ValueError("Raw-text field found in Git-safe boundary decisions")
    decisions_by_pair = {row["pair_id"]: row for row in decision_rows}
    for pair_id, (expected_id, expected_name) in EXPECTED_BOUNDARIES.items():
        row = decisions_by_pair[pair_id]
        if (int(row["canonical_label_id"]), row["canonical_label_name"]) != (expected_id, expected_name):
            raise ValueError(f"Canonical boundary mismatch for {pair_id}")
        if row["decision_source"] != "human_confirmed" or row["decision_status"] != "RESOLVED":
            raise ValueError(f"Human boundary is not resolved for {pair_id}")
        if row["canonical_label_name"] in {"CLARIFY_REQUIRED", "EXCLUDE_FROM_STRICT_BOUNDARY_EVIDENCE"}:
            raise ValueError(f"Targeted boundary remains unresolved for {pair_id}")
        for side in ("a", "b"):
            sample_id = row[f"sample_id_{side}"]
            if sample_id not in manifest_by_sample:
                raise ValueError(f"Unknown boundary sample: {sample_id}")
            if row[f"source_label_{side}"] != manifest_by_sample[sample_id]["label_name"]:
                raise ValueError(f"Frozen source label changed for {sample_id}")
    conflict_rows = read_csv(conflicts_path)
    if len(conflict_rows) != 3:
        raise ValueError("Source conflict register must preserve all three conflicts")
    with conflicts_path.open("r", encoding="utf-8-sig", newline="") as handle:
        fields = set(csv.DictReader(handle).fieldnames or [])
    if fields & UNSAFE_RAW_FIELDS:
        raise ValueError("Raw-text field found in Git-safe conflict register")
    for row in conflict_rows:
        if row["sample_id_a"] not in valid_samples or row["sample_id_b"] not in valid_samples:
            raise ValueError("Conflict register references an unknown sample ID")
        if row["label_a"] not in LABELS.values() or row["label_b"] not in LABELS.values():
            raise ValueError("Conflict register references an unknown label")
        pair_id = row["evidence_source"].rsplit(":", 1)[-1]
        decision = decisions_by_pair.get(pair_id)
        if decision is None:
            raise ValueError(f"Conflict has no human boundary decision: {pair_id}")
        if row["boundary_status"] != "RESOLVED_FOR_CANONICAL_ANNOTATION":
            raise ValueError(f"Conflict boundary is unresolved: {pair_id}")
        if row["boundary_decision_source"] != "human_confirmed":
            raise ValueError(f"Conflict boundary is not human-confirmed: {pair_id}")
        if (row["canonical_label_id"], row["canonical_label_name"]) != (
            decision["canonical_label_id"],
            decision["canonical_label_name"],
        ):
            raise ValueError(f"Conflict register canonical label mismatch: {pair_id}")

    return {
        "labels": len(definitions),
        "neighbor_pairs": len(matrix_rows),
        "conflicts": len(conflict_rows),
        "boundary_decisions": len(decision_rows),
        "unresolved_boundaries": 0,
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
    parser.add_argument("--decisions", type=Path, default=base / "human_boundary_decisions_v1.csv")
    args = parser.parse_args()
    result = validate_contract(root, args.contract, args.matrix, args.conflicts, args.decisions)
    print("INTENT CONTRACT VALIDATION: PASS")
    print(f"LABELS: {result['labels']}")
    print(f"PAIRWISE BOUNDARIES: {result['neighbor_pairs']}")
    print(f"SOURCE CONFLICTS: {result['conflicts']}")
    print(f"HUMAN BOUNDARIES: {result['boundary_decisions']}")
    print(f"UNRESOLVED TARGETED BOUNDARIES: {result['unresolved_boundaries']}")
    print(f"STATUS: {result['status']}")


if __name__ == "__main__":
    main()
