"""Validate the frozen NID5-SHIFT-V1 schema and immutable dependencies."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import yaml


EXPECTED_LABELS = {
    0: "NID Information Correction",
    1: "New NID Registration",
    2: "Lost/Stolen NID",
    3: "NID Online Problem",
    4: "Smart ID Card",
}
EXPECTED_CONDITIONS = {
    "C0": "ORIGINAL",
    "C1": "NATURAL_PARAPHRASE",
    "C2": "BANGLISH_SCRIPT_SHIFT",
    "C3": "CODE_MIXED",
    "C4": "TYPO_NOISE",
}
EXPECTED_DEPENDENCY_HASHES = {
    "phase0_split_sha256": "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1",
    "family_map_sha256": "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c",
    "ontology_manifest_sha256": "41dc39210d6ea603995788d4ddb0bfe8de4ca3a6c4aff62cf13d379c15ba1742",
}
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


def recursive_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(recursive_keys(child))
    return keys


def validate(root: Path, schema_path: Path, profile_path: Path, conditions_path: Path, manifest_path: Path) -> dict[str, int | str]:
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    conditions = read_csv(conditions_path)

    if schema.get("benchmark_id") != "NID5-SHIFT-V1" or manifest.get("benchmark_id") != "NID5-SHIFT-V1":
        raise ValueError("Benchmark ID mismatch")
    if schema.get("status") != "SCHEMA_FROZEN_V1" or manifest.get("status") != "SCHEMA_FROZEN_V1":
        raise ValueError("Challenge protocol is not SCHEMA_FROZEN_V1")
    labels = {int(row["label_id"]): row["label_name"] for row in schema.get("labels", [])}
    if labels != EXPECTED_LABELS:
        raise ValueError("Schema must contain exactly the five frozen labels")
    condition_map = {row["condition_id"]: row["condition_name"] for row in schema.get("conditions", [])}
    csv_condition_map = {row["condition_id"]: row["condition_name"] for row in conditions}
    if condition_map != EXPECTED_CONDITIONS or csv_condition_map != EXPECTED_CONDITIONS:
        raise ValueError("Schema and condition contract must contain exactly C0-C4")

    seed_target = schema["seed_target"]
    planned = schema["planned_size"]
    if seed_target["source_split"] != "test" or seed_target["total"] != 100 or seed_target["per_label"] != 20:
        raise ValueError("Seed target must be 100 TEST seeds with 20 per label")
    if planned["conditions"] != 5 or planned["total_instances"] != 500:
        raise ValueError("Planned benchmark must contain 500 matched instances")
    if not seed_target["one_seed_per_paraphrase_family"] or not schema["family_rules"]["one_seed_per_family"]:
        raise ValueError("One seed per family is not enforced")
    if not schema["family_rules"]["test_only_families_required"]:
        raise ValueError("TEST-only families are not required")
    eligibility = " ".join(schema["eligibility_rules"]).lower()
    if "no train member" not in eligibility or "no dev member" not in eligibility:
        raise ValueError("TRAIN/DEV family overlap is not prohibited")
    if "source-conflict" not in eligibility:
        raise ValueError("Known source conflicts are not excluded")
    if schema["clarify_required"]["challenge_class"] or schema["clarify_required"]["training_class"]:
        raise ValueError("CLARIFY_REQUIRED must not be a sixth class")
    if "out_of_domain_examples" not in schema["excluded_scopes"]:
        raise ValueError("OOD must be excluded from the Phase 1 benchmark")
    if not schema["review_requirements"]["review_before_evaluation"]:
        raise ValueError("Human semantic-preservation review is not mandatory")
    if schema["evaluation_policy"]["training_use"] != "prohibited" or schema["evaluation_policy"]["tuning_use"] != "prohibited":
        raise ValueError("Challenge data must be evaluation-only")
    if schema["future_selection_algorithm"]["python_hash_prohibited"] is not True:
        raise ValueError("Unstable Python hash ordering is not prohibited")
    if "SHA256" not in schema["future_selection_algorithm"]["deterministic_tie_key"]:
        raise ValueError("Stable SHA-256 tie ordering is missing")
    if schema["future_selection_algorithm"]["execute_in_this_task"] is not False:
        raise ValueError("Seed selection was incorrectly enabled")

    if profile["source_split"] != "test" or profile["total_test_samples"] != 218:
        raise ValueError("Seed-pool profile is not the frozen TEST population")
    if profile["final_seed_selection_executed"] or profile["sample_ids_emitted"] or profile["raw_text_emitted"]:
        raise ValueError("Profile selected/emitted seeds or raw text")
    if len(profile["per_label"]) != 5:
        raise ValueError("Pool profile must contain five labels")
    for row in profile["per_label"]:
        if int(row["label_id"]) not in EXPECTED_LABELS or row["label_name"] != EXPECTED_LABELS[int(row["label_id"])]:
            raise ValueError("Pool profile label mismatch")
        if row["required_seed_count"] != 20 or row["eligible_family_units"] < 20 or not row["feasible"]:
            raise ValueError(f"Insufficient eligible family units for label {row['label_id']}")
    if profile["excluded"]["family_crosses_train"] < 1:
        raise ValueError("Expected TRAIN-family exclusions are absent")
    if profile["excluded"]["source_label_conflict"] < 1:
        raise ValueError("Expected conflict exclusions are absent")

    dependency_paths = {
        "phase0_split_sha256": root / "research" / "phase0" / "nid_5class_split_manifest_v1.csv",
        "family_map_sha256": root / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv",
        "ontology_manifest_sha256": root / "research" / "phase1" / "ontology" / "nid_5class_ontology_manifest_v1.json",
    }
    for key, expected in EXPECTED_DEPENDENCY_HASHES.items():
        if sha256(dependency_paths[key]) != expected or manifest[key] != expected:
            raise ValueError(f"Frozen dependency hash mismatch: {key}")
    artifact_paths = {
        "schema_sha256": schema_path,
        "sampling_protocol_sha256": schema_path.parent / "CHALLENGE_SAMPLING_PROTOCOL_V1.md",
        "condition_contract_sha256": conditions_path,
        "seed_pool_profile_sha256": profile_path,
    }
    for key, path in artifact_paths.items():
        if sha256(path) != manifest[key]:
            raise ValueError(f"Protocol artifact hash mismatch: {key}")
    if recursive_keys(profile) & UNSAFE_RAW_FIELDS or recursive_keys(schema) & UNSAFE_RAW_FIELDS:
        raise ValueError("Raw-text field found in Git-safe schema/profile")
    with conditions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        if set(csv.DictReader(handle).fieldnames or []) & UNSAFE_RAW_FIELDS:
            raise ValueError("Raw-text field found in condition contract")
    if (schema_path.parent / "challenge_seed_panel_v1.csv").exists():
        raise ValueError("Final challenge seed panel must not exist in this task")

    return {
        "labels": len(labels),
        "conditions": len(condition_map),
        "target_seeds": seed_target["total"],
        "planned_instances": planned["total_instances"],
        "eligible_samples": profile["eligible_samples"],
        "eligible_family_units": profile["eligible_family_units"],
        "status": manifest["status"],
    }


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    base = root / "research" / "phase1" / "challenge_benchmark"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=base / "nid5_shift_challenge_schema_v1.yaml")
    parser.add_argument("--profile", type=Path, default=base / "challenge_seed_pool_profile_v1.json")
    parser.add_argument("--conditions", type=Path, default=base / "challenge_condition_contract_v1.csv")
    parser.add_argument("--manifest", type=Path, default=base / "challenge_protocol_manifest_v1.json")
    args = parser.parse_args()
    result = validate(root, args.schema, args.profile, args.conditions, args.manifest)
    print("CHALLENGE PROTOCOL VALIDATION: PASS")
    print(f"LABELS: {result['labels']}")
    print(f"CONDITIONS: {result['conditions']}")
    print(f"TARGET SEEDS: {result['target_seeds']}")
    print(f"PLANNED INSTANCES: {result['planned_instances']}")
    print(f"ELIGIBLE FAMILY UNITS: {result['eligible_family_units']}")
    print(f"STATUS: {result['status']}")


if __name__ == "__main__":
    main()
