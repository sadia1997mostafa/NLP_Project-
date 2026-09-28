from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research" / "phase1" / "challenge_benchmark"
SCHEMA_PATH = BASE / "nid5_shift_challenge_schema_v1.yaml"
PROFILE_PATH = BASE / "challenge_seed_pool_profile_v1.json"
MANIFEST_PATH = BASE / "challenge_protocol_manifest_v1.json"
CONDITIONS_PATH = BASE / "challenge_condition_contract_v1.csv"
EXPECTED_SPLIT_HASH = "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
EXPECTED_FAMILY_HASH = "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c"
EXPECTED_ONTOLOGY_HASH = "41dc39210d6ea603995788d4ddb0bfe8de4ca3a6c4aff62cf13d379c15ba1742"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def schema():
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def profile():
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def test_five_labels_five_conditions_and_planned_size():
    data = schema()
    assert len(data["labels"]) == 5
    assert [row["label_id"] for row in data["labels"]] == [0, 1, 2, 3, 4]
    assert len(data["conditions"]) == 5
    assert [row["condition_id"] for row in data["conditions"]] == ["C0", "C1", "C2", "C3", "C4"]
    assert data["seed_target"]["total"] == 100
    assert data["seed_target"]["per_label"] == 20
    assert data["planned_size"]["total_instances"] == 500


def test_stable_hash_specification_is_deterministic():
    profiler = load_module("pool_profiler", BASE / "profile_challenge_seed_pool.py")
    sample_id = "NID5-V1-000001"
    expected = hashlib.sha256(f"NID5-SHIFT-V1|SEED-V1|{sample_id}".encode("utf-8")).hexdigest()
    assert profiler.stable_key(sample_id) == expected
    assert profiler.stable_key(sample_id) == profiler.stable_key(sample_id)
    assert schema()["future_selection_algorithm"]["python_hash_prohibited"] is True


def test_test_only_family_clean_eligibility_and_feasibility():
    data = profile()
    assert data["source_split"] == "test"
    assert data["total_test_samples"] == 218
    assert data["excluded"]["family_crosses_train"] == 5
    assert data["excluded"]["family_crosses_dev"] == 0
    assert data["excluded"]["source_label_conflict"] == 2
    assert data["eligible_samples"] == 211
    assert data["eligible_family_units"] == 209
    assert [row["eligible_family_units"] for row in data["per_label"]] == [38, 65, 34, 44, 28]
    assert all(row["eligible_family_units"] >= 20 and row["feasible"] for row in data["per_label"])


def test_one_seed_per_family_and_no_seed_selection():
    data = schema()
    assert data["seed_target"]["one_seed_per_paraphrase_family"] is True
    assert data["family_rules"]["one_seed_per_family"] is True
    assert data["future_selection_algorithm"]["execute_in_this_task"] is False
    assert not (BASE / "challenge_seed_panel_v1.csv").exists()
    assert profile()["final_seed_selection_executed"] is False


def test_clarify_and_ood_are_not_challenge_classes():
    data = schema()
    assert data["clarify_required"] == {
        "role": "evaluation_annotation_state_only",
        "challenge_class": False,
        "training_class": False,
    }
    assert "out_of_domain_examples" in data["excluded_scopes"]
    assert "unknown_intent_detection_sets" in data["excluded_scopes"]


def test_transformations_cannot_change_label_and_failures_are_not_relabelled():
    data = schema()
    assert all(row["semantic_change_allowed"] is False for row in data["conditions"])
    assert "canonical coarse label" in data["semantic_preservation_rules"]["preserve"]
    assert data["semantic_preservation_rules"]["relabel_on_failure"] == "prohibited"
    assert set(data["semantic_preservation_rules"]["failed_transformation_policy"]) == {
        "REWRITE_REQUIRED",
        "REJECT",
    }


def test_human_review_and_evaluation_only_policy():
    data = schema()
    assert data["review_requirements"]["review_before_evaluation"] is True
    assert data["review_requirements"]["reviewer"] == "human"
    assert data["evaluation_policy"]["training_use"] == "prohibited"
    assert data["evaluation_policy"]["tuning_use"] == "prohibited"


def test_profile_rebuild_is_byte_equivalent_in_content():
    profiler = load_module("pool_profiler_rebuild", BASE / "profile_challenge_seed_pool.py")
    private_source = ROOT.parent / f"{ROOT.name}_private" / "phase0" / "nid_5class_source_v1.csv"
    rebuilt = profiler.profile(
        private_source,
        ROOT / "research" / "phase0" / "nid_5class_split_manifest_v1.csv",
        ROOT / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv",
        ROOT / "research" / "phase1" / "ontology" / "nid_5class_source_conflicts_v1.csv",
        ROOT / "research" / "phase1" / "ontology" / "nid_5class_ontology_manifest_v1.json",
    )
    assert rebuilt == profile()


def test_no_raw_text_or_sample_ids_in_git_safe_profile_and_schema():
    validator = load_module("challenge_validator_keys", BASE / "validate_challenge_protocol.py")
    unsafe = {"text", "text_a", "text_b", "query", "query_text", "raw_text"}
    assert not validator.recursive_keys(profile()) & unsafe
    assert not validator.recursive_keys(schema()) & unsafe
    serialized_profile = PROFILE_PATH.read_text(encoding="utf-8")
    assert "NID5-V1-" not in serialized_profile


def test_frozen_dependencies_unchanged_and_validator_passes():
    split = ROOT / "research" / "phase0" / "nid_5class_split_manifest_v1.csv"
    family = ROOT / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv"
    ontology = ROOT / "research" / "phase1" / "ontology" / "nid_5class_ontology_manifest_v1.json"
    assert hashlib.sha256(split.read_bytes()).hexdigest() == EXPECTED_SPLIT_HASH
    assert hashlib.sha256(family.read_bytes()).hexdigest() == EXPECTED_FAMILY_HASH
    assert hashlib.sha256(ontology.read_bytes()).hexdigest() == EXPECTED_ONTOLOGY_HASH
    validator = load_module("challenge_validator", BASE / "validate_challenge_protocol.py")
    result = validator.validate(ROOT, SCHEMA_PATH, PROFILE_PATH, CONDITIONS_PATH, MANIFEST_PATH)
    assert result == {
        "labels": 5,
        "conditions": 5,
        "target_seeds": 100,
        "planned_instances": 500,
        "eligible_samples": 211,
        "eligible_family_units": 209,
        "status": "SCHEMA_FROZEN_V1",
    }
