from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research" / "phase1" / "ontology"
CONTRACT = BASE / "nid_5class_intent_contract_v1.yaml"
MATRIX = BASE / "nid_5class_confusing_neighbor_matrix_v1.csv"
CONFLICTS = BASE / "nid_5class_source_conflicts_v1.csv"
DECISIONS = BASE / "human_boundary_decisions_v1.csv"
EXPECTED_FAMILY_HASH = "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c"


def load_validator():
    spec = importlib.util.spec_from_file_location("intent_validator", BASE / "validate_intent_contract.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_contract_structure_and_frozen_labels():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert contract["status"] == "FROZEN_V1"
    assert contract["clarify_is_training_label"] is False
    definitions = contract["labels"]
    assert len(definitions) == 5
    assert [row["label_id"] for row in definitions] == [0, 1, 2, 3, 4]
    frozen = json.loads((ROOT / "research" / "phase0" / "nid_5class_labels_v1.json").read_text(encoding="utf-8"))
    assert [row["label_name"] for row in definitions] == [row["label_name"] for row in frozen["labels"]]
    for row in definitions:
        assert row["short_definition"]
        assert row["include_when"]
        assert row["exclude_when"]
        assert row["clarification_triggers"]


def test_all_pairwise_boundaries_and_valid_conflicts():
    with MATRIX.open("r", encoding="utf-8", newline="") as handle:
        matrix = list(csv.DictReader(handle))
    assert len(matrix) == 10
    assert len({frozenset((row["label_a"], row["label_b"])) for row in matrix}) == 10
    manifest_path = ROOT / "research" / "phase0" / "nid_5class_split_manifest_v1.csv"
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        valid_samples = {row["sample_id"] for row in csv.DictReader(handle)}
    with CONFLICTS.open("r", encoding="utf-8", newline="") as handle:
        conflicts = list(csv.DictReader(handle))
    assert len(conflicts) == 3
    assert all(row["sample_id_a"] in valid_samples and row["sample_id_b"] in valid_samples for row in conflicts)


def test_human_boundaries_and_historical_source_labels():
    with DECISIONS.open("r", encoding="utf-8", newline="") as handle:
        decisions = {row["pair_id"]: row for row in csv.DictReader(handle)}
    assert len(decisions) == 3
    assert decisions["NID5-ND-000048"]["canonical_label_name"] == "Smart ID Card"
    assert decisions["NID5-ND-000050"]["canonical_label_name"] == "Smart ID Card"
    assert decisions["NID5-ND-000071"]["canonical_label_name"] == "Lost/Stolen NID"
    assert all(row["decision_source"] == "human_confirmed" for row in decisions.values())
    assert all(row["decision_status"] == "RESOLVED" for row in decisions.values())
    manifest_path = ROOT / "research" / "phase0" / "nid_5class_split_manifest_v1.csv"
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        frozen = {row["sample_id"]: row["label_name"] for row in csv.DictReader(handle)}
    for row in decisions.values():
        assert frozen[row["sample_id_a"]] == row["source_label_a"]
        assert frozen[row["sample_id_b"]] == row["source_label_b"]


def test_conflict_register_preserves_history_and_resolves_canonical_boundary():
    with CONFLICTS.open("r", encoding="utf-8", newline="") as handle:
        conflicts = list(csv.DictReader(handle))
    assert len(conflicts) == 3
    assert all(row["status"] == "DOCUMENTED" for row in conflicts)
    assert all(row["boundary_status"] == "RESOLVED_FOR_CANONICAL_ANNOTATION" for row in conflicts)
    assert all(row["boundary_decision_source"] == "human_confirmed" for row in conflicts)


def test_git_safe_outputs_have_no_raw_text_fields():
    unsafe = {"text", "text_a", "text_b", "query", "query_text", "raw_text"}
    for path in (MATRIX, CONFLICTS, DECISIONS):
        with path.open("r", encoding="utf-8", newline="") as handle:
            fields = set(csv.DictReader(handle).fieldnames or [])
        assert not fields & unsafe


def test_private_outputs_are_outside_repository():
    private_root = ROOT.parent / f"{ROOT.name}_private" / "phase1"
    evidence = private_root / "label_definition_evidence_v1.csv"
    queue = private_root / "label_boundary_review_queue_v1.csv"
    resolved = private_root / "label_boundary_review_v1_resolved.csv"
    assert evidence.exists() and queue.exists() and resolved.exists()
    assert not evidence.is_relative_to(ROOT)
    assert not queue.is_relative_to(ROOT)
    assert not resolved.is_relative_to(ROOT)


def test_phase0_and_final_family_map_unchanged():
    family = ROOT / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv"
    assert hashlib.sha256(family.read_bytes()).hexdigest() == EXPECTED_FAMILY_HASH
    result = load_validator().validate_contract(ROOT, CONTRACT, MATRIX, CONFLICTS, DECISIONS)
    assert result == {
        "labels": 5,
        "neighbor_pairs": 10,
        "conflicts": 3,
        "boundary_decisions": 3,
        "unresolved_boundaries": 0,
        "samples": 1454,
        "status": "FROZEN_V1",
    }
