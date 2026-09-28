"""Verify the frozen Phase 1 five-class intent ontology without model evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from validate_intent_contract import validate_contract


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        raise ValueError(f"Missing {label}: {path}")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: expected {expected}, got {actual}")


def verify(root: Path, manifest_path: Path) -> dict[str, int | str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("ontology_status") != "FROZEN_V1":
        raise ValueError("Ontology manifest is not FROZEN_V1")
    if manifest.get("human_boundary_review_status") != "COMPLETE_TARGETED_REVIEW":
        raise ValueError("Targeted human boundary review is not complete")
    if manifest.get("annotation_scope") != "FIVE_CLASS_CANONICAL_CONTRACT":
        raise ValueError("Unexpected ontology annotation scope")
    if manifest.get("unresolved_targeted_boundaries") != 0:
        raise ValueError("Targeted boundary cases remain unresolved")

    ontology = root / "research" / "phase1" / "ontology"
    phase0 = root / "research" / "phase0"
    families = root / "research" / "phase1" / "paraphrase_families"
    private_phase1 = root.parent / f"{root.name}_private" / "phase1"
    private_source = root.parent / f"{root.name}_private" / "phase0" / "nid_5class_source_v1.csv"

    artifact_hashes = {
        "human_boundary_decisions_sha256": ontology / "human_boundary_decisions_v1.csv",
        "intent_contract_sha256": ontology / "nid_5class_intent_contract_v1.yaml",
        "annotation_policy_sha256": ontology / "nid_5class_annotation_policy_v1.md",
        "neighbor_matrix_sha256": ontology / "nid_5class_confusing_neighbor_matrix_v1.csv",
        "source_conflict_register_sha256": ontology / "nid_5class_source_conflicts_v1.csv",
        "phase0_label_sha256": phase0 / "nid_5class_labels_v1.json",
        "phase1_family_map_sha256": families / "paraphrase_family_map_v1.csv",
        "private_boundary_review_sha256": private_phase1 / "label_boundary_review_queue_v1.csv",
        "resolved_boundary_review_sha256": private_phase1 / "label_boundary_review_v1_resolved.csv",
        "phase0_source_sha256": private_source,
    }
    for key, path in artifact_hashes.items():
        require_hash(path, manifest[key], key)

    result = validate_contract(
        root,
        ontology / "nid_5class_intent_contract_v1.yaml",
        ontology / "nid_5class_confusing_neighbor_matrix_v1.csv",
        ontology / "nid_5class_source_conflicts_v1.csv",
        ontology / "human_boundary_decisions_v1.csv",
    )
    if result["labels"] != 5 or result["neighbor_pairs"] != 10:
        raise ValueError("Frozen label or neighbor-pair inventory mismatch")
    if result["conflicts"] != 3 or result["boundary_decisions"] != 3:
        raise ValueError("Conflict or human-boundary inventory mismatch")
    if result["unresolved_boundaries"] != 0:
        raise ValueError("Human boundary decisions remain unresolved")
    return result


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=root / "research" / "phase1" / "ontology" / "nid_5class_ontology_manifest_v1.json",
    )
    args = parser.parse_args()
    result = verify(root, args.manifest)
    print("ONTOLOGY FREEZE VERIFICATION: PASS")
    print(f"LABELS: {result['labels']}")
    print(f"PAIRWISE BOUNDARIES: {result['neighbor_pairs']}")
    print(f"HUMAN BOUNDARIES: {result['boundary_decisions']}")
    print(f"UNRESOLVED TARGETED BOUNDARIES: {result['unresolved_boundaries']}")
    print("ONTOLOGY STATUS: FROZEN_V1")


if __name__ == "__main__":
    main()
