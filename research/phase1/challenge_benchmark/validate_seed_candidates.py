"""Validate the deterministic NID5-SHIFT-V1 candidate and reserve artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from select_challenge_seed_candidates import (
    EXPECTED_ELIGIBLE_FAMILIES,
    EXPECTED_FAMILY_HASH,
    EXPECTED_ONTOLOGY_MANIFEST_HASH,
    EXPECTED_PROTOCOL_MANIFEST_HASH,
    EXPECTED_SOURCE_HASH,
    EXPECTED_SPLIT_HASH,
    LABELS,
    LENGTH_ORDER,
    REVIEW_FIELDS,
    SCRIPT_ORDER,
    read_csv,
    reconstruct_eligible_units,
    repository_root,
    sha256,
    stable_key,
)


def validate(
    source_path: Path,
    split_path: Path,
    family_path: Path,
    conflicts_path: Path,
    ontology_manifest_path: Path,
    protocol_manifest_path: Path,
    candidate_path: Path,
    reserve_path: Path,
    profile_path: Path,
    selection_manifest_path: Path,
    private_review_path: Path,
) -> dict[str, int]:
    manifest = json.loads(selection_manifest_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    candidates = read_csv(candidate_path)
    reserve = read_csv(reserve_path)
    review = read_csv(private_review_path)
    units, _ = reconstruct_eligible_units(
        source_path, split_path, family_path, conflicts_path,
        ontology_manifest_path, protocol_manifest_path,
    )

    expected_hashes = {
        "phase0_source_sha256": (source_path, EXPECTED_SOURCE_HASH),
        "phase0_split_sha256": (split_path, EXPECTED_SPLIT_HASH),
        "family_map_sha256": (family_path, EXPECTED_FAMILY_HASH),
        "ontology_manifest_sha256": (ontology_manifest_path, EXPECTED_ONTOLOGY_MANIFEST_HASH),
        "challenge_protocol_manifest_sha256": (protocol_manifest_path, EXPECTED_PROTOCOL_MANIFEST_HASH),
        "candidate_panel_sha256": (candidate_path, manifest["candidate_panel_sha256"]),
        "reserve_order_sha256": (reserve_path, manifest["reserve_order_sha256"]),
        "candidate_profile_sha256": (profile_path, manifest["candidate_profile_sha256"]),
        "private_review_queue_sha256": (private_review_path, manifest["private_review_queue_sha256"]),
    }
    for field, (path, expected) in expected_hashes.items():
        actual = sha256(path)
        if actual != expected or manifest[field] != expected:
            raise ValueError(f"Hash validation failed for {field}")

    if len(candidates) != 100 or len(review) != 100:
        raise ValueError("Candidate and review queues must contain exactly 100 rows")
    if len(reserve) != 109 or len(units) != 209:
        raise ValueError("Expected 209 units partitioned into 100 candidates and 109 reserves")
    per_label = Counter(int(row["label_id"]) for row in candidates)
    if per_label != Counter({label_id: 20 for label_id in LABELS}):
        raise ValueError(f"Candidate label quota mismatch: {per_label}")
    if manifest["eligible_family_unit_counts"] != {str(k): v for k, v in EXPECTED_ELIGIBLE_FAMILIES.items()}:
        raise ValueError("Frozen eligible-family counts differ")

    sample_ids = [row["sample_id"] for row in candidates]
    families = [row["paraphrase_family_id"] for row in candidates]
    if len(set(sample_ids)) != 100 or len(set(families)) != 100:
        raise ValueError("Candidate sample IDs and families must be unique")
    unit_by_id = {str(row["sample_id"]): row for row in units}
    family_rows = read_csv(family_path)
    family_splits: dict[str, set[str]] = defaultdict(set)
    for row in family_rows:
        family_splits[row["paraphrase_family_id"]].add(row["phase0_split"])
    conflicts = {
        sample_id for row in read_csv(conflicts_path)
        for sample_id in (row["sample_id_a"], row["sample_id_b"])
    }
    for row in candidates:
        sample_id = row["sample_id"]
        if sample_id not in unit_by_id or row["phase0_split"] != "test":
            raise ValueError(f"Candidate is not in the reconstructed TEST-only pool: {sample_id}")
        if "train" in family_splits[row["paraphrase_family_id"]] or "dev" in family_splits[row["paraphrase_family_id"]]:
            raise ValueError(f"Candidate family overlaps TRAIN/DEV: {sample_id}")
        if sample_id in conflicts:
            raise ValueError(f"Source-conflict sample selected: {sample_id}")
        if row["script_profile"] not in SCRIPT_ORDER or row["length_band"] not in LENGTH_ORDER:
            raise ValueError(f"Invalid coverage stratum: {sample_id}")
        if row["stable_selection_hash"] != stable_key(sample_id):
            raise ValueError(f"Stable selection hash mismatch: {sample_id}")
        if row["selection_status"] != "PENDING_HUMAN_REVIEW":
            raise ValueError(f"Candidate review state was pre-decided: {sample_id}")

    reserve_ids = [row["sample_id"] for row in reserve]
    reserve_families = [row["paraphrase_family_id"] for row in reserve]
    if len(set(reserve_ids)) != len(reserve) or len(set(reserve_families)) != len(reserve):
        raise ValueError("Reserve rows are not unique family units")
    if set(sample_ids) & set(reserve_ids) or set(families) & set(reserve_families):
        raise ValueError("Candidate and reserve partitions overlap")
    if set(sample_ids) | set(reserve_ids) != set(unit_by_id):
        raise ValueError("Candidate plus reserve IDs do not cover the eligible family-unit representatives")
    for row in reserve:
        if row["stable_selection_hash"] != stable_key(row["sample_id"]):
            raise ValueError(f"Reserve stable hash mismatch: {row['sample_id']}")

    if tuple(review[0]) != REVIEW_FIELDS:
        raise ValueError("Private review queue schema mismatch")
    if [row["sample_id"] for row in review] != sample_ids:
        raise ValueError("Private review queue does not mirror candidate IDs/order")
    for row in review:
        for field in ("classifiable", "explicit_enough", "transformable", "review_decision", "human_notes"):
            if row[field]:
                raise ValueError(f"Private review field {field} was not initially blank")

    banned_headers = {"text", "text_a", "text_b", "query", "raw_text"}
    for path in (candidate_path, reserve_path):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            headers = set(next(csv.reader(handle)))
        if headers & banned_headers:
            raise ValueError(f"Raw-text field found in Git-safe CSV: {path}")
    if profile.get("raw_text_emitted") is not False or manifest.get("raw_text_in_git_artifacts") is not False:
        raise ValueError("Git-safe metadata does not explicitly deny raw text")
    if profile.get("unique_sample_ids") != 100 or profile.get("unique_families") != 100:
        raise ValueError("Candidate profile uniqueness mismatch")
    if profile.get("final_seed_panel_frozen") is not False:
        raise ValueError("Candidate profile incorrectly freezes final seed panel")
    if manifest.get("human_review_status") != "PENDING" or manifest.get("final_seed_status") != "NOT_FROZEN":
        raise ValueError("Selection manifest review/freeze state mismatch")
    return {"candidates": len(candidates), "reserve": len(reserve), "eligible_units": len(units)}


def main() -> None:
    root = repository_root()
    private_root = root.parent / f"{root.name}_private"
    base = root / "research" / "phase1" / "challenge_benchmark"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=private_root / "phase0" / "nid_5class_source_v1.csv")
    parser.add_argument("--split-manifest", type=Path, default=root / "research" / "phase0" / "nid_5class_split_manifest_v1.csv")
    parser.add_argument("--family-map", type=Path, default=root / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv")
    parser.add_argument("--conflicts", type=Path, default=root / "research" / "phase1" / "ontology" / "nid_5class_source_conflicts_v1.csv")
    parser.add_argument("--ontology-manifest", type=Path, default=root / "research" / "phase1" / "ontology" / "nid_5class_ontology_manifest_v1.json")
    parser.add_argument("--protocol-manifest", type=Path, default=base / "challenge_protocol_manifest_v1.json")
    parser.add_argument("--candidates", type=Path, default=base / "challenge_seed_candidates_v1.csv")
    parser.add_argument("--reserve", type=Path, default=base / "challenge_seed_reserve_order_v1.csv")
    parser.add_argument("--profile", type=Path, default=base / "challenge_seed_candidate_profile_v1.json")
    parser.add_argument("--selection-manifest", type=Path, default=base / "challenge_seed_selection_manifest_v1.json")
    parser.add_argument("--private-review", type=Path, default=private_root / "phase1" / "challenge_seed_review_queue_v1.csv")
    args = parser.parse_args()
    counts = validate(
        args.source, args.split_manifest, args.family_map, args.conflicts,
        args.ontology_manifest, args.protocol_manifest, args.candidates,
        args.reserve, args.profile, args.selection_manifest, args.private_review,
    )
    print("CHALLENGE SEED CANDIDATE VALIDATION: PASS")
    print(f"ELIGIBLE FAMILY UNITS: {counts['eligible_units']}")
    print(f"CANDIDATES: {counts['candidates']}")
    print(f"RESERVE ROWS: {counts['reserve']}")
    print("HUMAN REVIEW COMPLETED: 0 / 100")
    print("FINAL SEED PANEL FROZEN: NO")


if __name__ == "__main__":
    main()
