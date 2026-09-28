"""Profile the aggregate NID5-SHIFT-V1 TEST seed pool without selecting IDs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


BENCHMARK_ID = "NID5-SHIFT-V1"
SELECTION_SALT = "NID5-SHIFT-V1|SEED-V1|"
EXPECTED_SPLIT_HASH = "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
EXPECTED_FAMILY_HASH = "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c"
EXPECTED_ONTOLOGY_MANIFEST_HASH = "41dc39210d6ea603995788d4ddb0bfe8de4ca3a6c4aff62cf13d379c15ba1742"
LABELS = {
    0: "NID Information Correction",
    1: "New NID Registration",
    2: "Lost/Stolen NID",
    3: "NID Online Problem",
    4: "Smart ID Card",
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def stable_key(sample_id: str) -> str:
    return hashlib.sha256(f"{SELECTION_SALT}{sample_id}".encode("utf-8")).hexdigest()


def script_profile(text: str) -> str:
    bengali = 0
    latin = 0
    for character in text:
        if not character.isalpha():
            continue
        codepoint = ord(character)
        if 0x0980 <= codepoint <= 0x09FF:
            bengali += 1
        elif (0x0041 <= codepoint <= 0x005A) or (0x0061 <= codepoint <= 0x007A):
            latin += 1
    total = bengali + latin
    if total == 0:
        return "MIXED_SCRIPT"
    if bengali / total >= 0.80:
        return "BENGALI_SCRIPT_DOMINANT"
    if latin / total >= 0.80:
        return "LATIN_SCRIPT_DOMINANT"
    return "MIXED_SCRIPT"


def assign_length_bands(rows: list[dict[str, object]]) -> None:
    by_label: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_label[int(row["label_id"])].append(row)
    names = ("SHORT", "MEDIUM", "LONG")
    for label_rows in by_label.values():
        ordered = sorted(
            label_rows,
            key=lambda row: (int(row["normalized_length"]), stable_key(str(row["sample_id"])), str(row["sample_id"])),
        )
        size = len(ordered)
        for rank, row in enumerate(ordered):
            row["length_band"] = names[min(2, (rank * 3) // size)]


def profile(
    source_path: Path,
    split_path: Path,
    family_path: Path,
    conflicts_path: Path,
    ontology_manifest_path: Path,
) -> dict[str, object]:
    if sha256(split_path) != EXPECTED_SPLIT_HASH:
        raise ValueError("Frozen Phase 0 split hash mismatch")
    if sha256(family_path) != EXPECTED_FAMILY_HASH:
        raise ValueError("Frozen family-map hash mismatch")
    if sha256(ontology_manifest_path) != EXPECTED_ONTOLOGY_MANIFEST_HASH:
        raise ValueError("Frozen ontology-manifest hash mismatch")

    split_rows = read_csv(split_path)
    family_rows = read_csv(family_path)
    conflict_rows = read_csv(conflicts_path)
    source_rows = read_csv(source_path)
    if len(split_rows) != 1454 or len(family_rows) != 1454 or len(source_rows) != 1454:
        raise ValueError("Frozen input row-count mismatch")

    source_by_row = {index: row for index, row in enumerate(source_rows, start=1)}
    family_by_sample = {row["sample_id"]: row for row in family_rows}
    family_splits: dict[str, set[str]] = defaultdict(set)
    for row in family_rows:
        family_splits[row["paraphrase_family_id"]].add(row["phase0_split"])
    conflicts = {
        sample_id
        for row in conflict_rows
        for sample_id in (row["sample_id_a"], row["sample_id_b"])
    }

    test_rows = [row for row in split_rows if row["split"] == "test"]
    exclusions = Counter()
    exclusion_by_label: dict[int, Counter[str]] = defaultdict(Counter)
    eligible: list[dict[str, object]] = []
    for row in test_rows:
        label_id = int(row["label_id"])
        sample_id = row["sample_id"]
        family = family_by_sample.get(sample_id)
        source = source_by_row.get(int(row["source_row_number"]))
        reason = ""
        if family is None or source is None:
            reason = "other_protocol_reason"
        elif family["label_id"] != row["label_id"] or family["label_name"] != row["label_name"]:
            reason = "other_protocol_reason"
        elif "train" in family_splits[family["paraphrase_family_id"]]:
            reason = "family_crosses_train"
        elif "dev" in family_splits[family["paraphrase_family_id"]]:
            reason = "family_crosses_dev"
        elif sample_id in conflicts:
            reason = "source_label_conflict"
        else:
            text = normalize_text(source.get("text", ""))
            if not text or row["label_name"] != source.get("problem") or label_id not in LABELS:
                reason = "other_protocol_reason"
            else:
                eligible.append(
                    {
                        "sample_id": sample_id,
                        "label_id": label_id,
                        "label_name": row["label_name"],
                        "family_id": family["paraphrase_family_id"],
                        "normalized_length": len(text),
                        "script_profile": script_profile(text),
                    }
                )
        if reason:
            exclusions[reason] += 1
            exclusion_by_label[label_id][reason] += 1

    assign_length_bands(eligible)
    test_by_label = Counter(int(row["label_id"]) for row in test_rows)
    eligible_by_label: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in eligible:
        eligible_by_label[int(row["label_id"])].append(row)

    per_label: list[dict[str, object]] = []
    for label_id, label_name in LABELS.items():
        rows = eligible_by_label[label_id]
        family_count = len({str(row["family_id"]) for row in rows})
        per_label.append(
            {
                "label_id": label_id,
                "label_name": label_name,
                "test_total": test_by_label[label_id],
                "eligible_samples": len(rows),
                "eligible_family_units": family_count,
                "required_seed_count": 20,
                "feasible": family_count >= 20,
                "exclusions": dict(sorted(exclusion_by_label[label_id].items())),
                "script_profiles": dict(sorted(Counter(str(row["script_profile"]) for row in rows).items())),
                "length_bands": dict(sorted(Counter(str(row["length_band"]) for row in rows).items())),
            }
        )
    if any(not row["feasible"] for row in per_label):
        raise ValueError("At least one frozen label has fewer than 20 eligible TEST-only family units")

    return {
        "benchmark_id": BENCHMARK_ID,
        "profile_version": "CHALLENGE-SEED-POOL-PROFILE-V1",
        "profile_status": "FEASIBLE_WITH_MANDATORY_HUMAN_SEMANTIC_GATE",
        "source_split": "test",
        "total_test_samples": len(test_rows),
        "eligible_samples": len(eligible),
        "eligible_family_units": len({str(row["family_id"]) for row in eligible}),
        "excluded": {
            "family_crosses_train": exclusions["family_crosses_train"],
            "family_crosses_dev": exclusions["family_crosses_dev"],
            "source_label_conflict": exclusions["source_label_conflict"],
            "other_protocol_reason": exclusions["other_protocol_reason"],
        },
        "eligibility_precedence": [
            "missing_or_inconsistent_frozen_input",
            "family_crosses_train",
            "family_crosses_dev",
            "source_label_conflict",
            "missing_text_or_label_mismatch",
            "eligible",
        ],
        "per_label": per_label,
        "coverage_strata": {
            "script_profile_method": "Count Bengali and ASCII-Latin alphabetic code points; >=80% is dominant, otherwise mixed.",
            "length_band_method": "Within-label rank tertiles by NFC/whitespace-normalized code-point length; stable SHA-256 ordering breaks length ties.",
        },
        "human_semantic_gate": {
            "required_before_seed_freeze": True,
            "requirements": [
                "CLASSIFIABLE under FROZEN_V1",
                "explicit requested action and sufficient lifecycle context",
                "future transformations can preserve the decisive boundary information",
            ],
            "failure_policy": "Reject the candidate and continue deterministic ordering; never change its label.",
        },
        "sample_ids_emitted": False,
        "final_seed_selection_executed": False,
        "raw_text_emitted": False,
    }


def main() -> None:
    root = repository_root()
    private_source = root.parent / f"{root.name}_private" / "phase0" / "nid_5class_source_v1.csv"
    base = root / "research" / "phase1" / "challenge_benchmark"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=private_source)
    parser.add_argument("--split-manifest", type=Path, default=root / "research" / "phase0" / "nid_5class_split_manifest_v1.csv")
    parser.add_argument("--family-map", type=Path, default=root / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv")
    parser.add_argument("--conflicts", type=Path, default=root / "research" / "phase1" / "ontology" / "nid_5class_source_conflicts_v1.csv")
    parser.add_argument("--ontology-manifest", type=Path, default=root / "research" / "phase1" / "ontology" / "nid_5class_ontology_manifest_v1.json")
    parser.add_argument("--output", type=Path, default=base / "challenge_seed_pool_profile_v1.json")
    args = parser.parse_args()
    result = profile(args.source, args.split_manifest, args.family_map, args.conflicts, args.ontology_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("CHALLENGE SEED POOL PROFILE: PASS")
    print(f"TEST SAMPLES: {result['total_test_samples']}")
    print(f"ELIGIBLE SAMPLES: {result['eligible_samples']}")
    print(f"ELIGIBLE FAMILY UNITS: {result['eligible_family_units']}")
    for row in result["per_label"]:
        print(f"{row['label_id']} {row['label_name']}: {row['eligible_family_units']} family units (required 20)")
    print("FINAL SEED SELECTION EXECUTED: NO")


if __name__ == "__main__":
    main()
