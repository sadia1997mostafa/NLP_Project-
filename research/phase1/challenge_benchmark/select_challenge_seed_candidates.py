"""Select deterministic NID5-SHIFT-V1 seed candidates and prepare private review."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


BENCHMARK_ID = "NID5-SHIFT-V1"
SELECTION_VERSION = "SEED-V1"
SELECTION_SALT = f"{BENCHMARK_ID}|{SELECTION_VERSION}|"
STARTING_COMMIT = "191db1c3cf82504ba9b65c4fe44547279d62bfeb"
EXPECTED_SOURCE_HASH = "6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa"
EXPECTED_SPLIT_HASH = "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
EXPECTED_FAMILY_HASH = "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c"
EXPECTED_ONTOLOGY_MANIFEST_HASH = "41dc39210d6ea603995788d4ddb0bfe8de4ca3a6c4aff62cf13d379c15ba1742"
EXPECTED_PROTOCOL_MANIFEST_HASH = "5516d8ae9d9e83d29fb8b0d08ff1a440efd41769e35666d58d1b17c3991e0326"
EXPECTED_ELIGIBLE_FAMILIES = {0: 38, 1: 65, 2: 34, 3: 44, 4: 28}
LABELS = {
    0: "NID Information Correction",
    1: "New NID Registration",
    2: "Lost/Stolen NID",
    3: "NID Online Problem",
    4: "Smart ID Card",
}
SCRIPT_ORDER = ("BENGALI_SCRIPT_DOMINANT", "LATIN_SCRIPT_DOMINANT", "MIXED_SCRIPT")
LENGTH_ORDER = ("SHORT", "MEDIUM", "LONG")
CANDIDATE_FIELDS = (
    "candidate_seed_index", "sample_id", "label_id", "label_name", "phase0_split",
    "paraphrase_family_id", "family_size", "script_profile", "length_band",
    "stable_selection_hash", "selection_rank", "selection_status",
)
RESERVE_FIELDS = (
    "reserve_rank_global", "reserve_rank_within_label", "sample_id", "label_id",
    "label_name", "paraphrase_family_id", "script_profile", "length_band",
    "stable_selection_hash",
)
REVIEW_FIELDS = (
    "review_index", "sample_id", "text", "source_label_id", "source_label_name",
    "canonical_label_id", "canonical_label_name", "phase0_split",
    "paraphrase_family_id", "script_profile", "length_band", "classifiable",
    "explicit_enough", "transformable", "review_decision", "human_notes",
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_key(sample_id: str) -> str:
    return hashlib.sha256(f"{SELECTION_SALT}{sample_id}".encode("utf-8")).hexdigest()


def normalize_text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def script_profile(text: str) -> str:
    bengali = 0
    latin = 0
    for character in text:
        if not character.isalpha():
            continue
        codepoint = ord(character)
        if 0x0980 <= codepoint <= 0x09FF:
            bengali += 1
        elif 0x0041 <= codepoint <= 0x005A or 0x0061 <= codepoint <= 0x007A:
            latin += 1
    total = bengali + latin
    if total == 0:
        return "MIXED_SCRIPT"
    if bengali / total >= 0.80:
        return "BENGALI_SCRIPT_DOMINANT"
    if latin / total >= 0.80:
        return "LATIN_SCRIPT_DOMINANT"
    return "MIXED_SCRIPT"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: Iterable[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_hash(path: Path, expected: str, name: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{name} hash mismatch: expected {expected}, got {actual}")


def assign_length_bands(rows: list[dict[str, object]]) -> None:
    by_label: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_label[int(row["label_id"])].append(row)
    for label_rows in by_label.values():
        ordered = sorted(
            label_rows,
            key=lambda row: (
                int(row["normalized_length"]),
                str(row["stable_selection_hash"]),
                str(row["sample_id"]),
            ),
        )
        size = len(ordered)
        for rank, row in enumerate(ordered):
            row["length_band"] = LENGTH_ORDER[min(2, (rank * 3) // size)]


def reconstruct_eligible_units(
    source_path: Path,
    split_path: Path,
    family_path: Path,
    conflicts_path: Path,
    ontology_manifest_path: Path,
    protocol_manifest_path: Path,
) -> tuple[list[dict[str, object]], dict[str, str]]:
    verify_hash(source_path, EXPECTED_SOURCE_HASH, "Phase 0 source")
    verify_hash(split_path, EXPECTED_SPLIT_HASH, "Phase 0 split")
    verify_hash(family_path, EXPECTED_FAMILY_HASH, "family map")
    verify_hash(ontology_manifest_path, EXPECTED_ONTOLOGY_MANIFEST_HASH, "ontology manifest")
    verify_hash(protocol_manifest_path, EXPECTED_PROTOCOL_MANIFEST_HASH, "challenge protocol manifest")

    source_rows = read_csv(source_path)
    split_rows = read_csv(split_path)
    family_rows = read_csv(family_path)
    conflict_rows = read_csv(conflicts_path)
    if len(source_rows) != 1454 or len(split_rows) != 1454 or len(family_rows) != 1454:
        raise ValueError("Frozen input row-count mismatch")

    source_by_row = {index: row for index, row in enumerate(source_rows, start=1)}
    family_by_sample = {row["sample_id"]: row for row in family_rows}
    family_splits: dict[str, set[str]] = defaultdict(set)
    for row in family_rows:
        family_splits[row["paraphrase_family_id"]].add(row["phase0_split"])
    conflict_ids = {
        sample_id
        for row in conflict_rows
        for sample_id in (row["sample_id_a"], row["sample_id_b"])
    }

    eligible_rows: list[dict[str, object]] = []
    texts: dict[str, str] = {}
    for split_row in split_rows:
        if split_row["split"] != "test":
            continue
        sample_id = split_row["sample_id"]
        label_id = int(split_row["label_id"])
        family = family_by_sample.get(sample_id)
        source = source_by_row.get(int(split_row["source_row_number"]))
        if label_id not in LABELS or split_row["label_name"] != LABELS[label_id]:
            raise ValueError(f"Frozen label mismatch for {sample_id}")
        if family is None or source is None:
            raise ValueError(f"Missing frozen source/family row for {sample_id}")
        if family["phase0_split"] != "test" or family["label_id"] != split_row["label_id"]:
            raise ValueError(f"Frozen family metadata mismatch for {sample_id}")
        family_id = family["paraphrase_family_id"]
        if "train" in family_splits[family_id] or "dev" in family_splits[family_id]:
            continue
        if sample_id in conflict_ids:
            continue
        text = normalize_text(source.get("text", ""))
        if not text or source.get("problem") != split_row["label_name"]:
            raise ValueError(f"Frozen source text/label mismatch for {sample_id}")
        texts[sample_id] = str(source.get("text", ""))
        eligible_rows.append(
            {
                "sample_id": sample_id,
                "label_id": label_id,
                "label_name": split_row["label_name"],
                "phase0_split": "test",
                "paraphrase_family_id": family_id,
                "family_size": int(family["family_size"]),
                "normalized_length": len(text),
                "script_profile": script_profile(text),
                "stable_selection_hash": stable_key(sample_id),
            }
        )
    assign_length_bands(eligible_rows)

    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in eligible_rows:
        by_family[str(row["paraphrase_family_id"])].append(row)
    units: list[dict[str, object]] = []
    for family_id in sorted(by_family):
        members = by_family[family_id]
        if len({int(row["label_id"]) for row in members}) != 1:
            raise ValueError(f"Eligible family crosses labels: {family_id}")
        units.append(min(members, key=lambda row: (str(row["stable_selection_hash"]), str(row["sample_id"]))))

    counts = Counter(int(row["label_id"]) for row in units)
    if dict(sorted(counts.items())) != EXPECTED_ELIGIBLE_FAMILIES:
        raise ValueError(
            "FROZEN ELIGIBILITY RECONSTRUCTION FAILURE: "
            f"expected {EXPECTED_ELIGIBLE_FAMILIES}, got {dict(sorted(counts.items()))}"
        )
    return units, texts


def _ordered_from_strata(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    queues: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        queues[(str(row["script_profile"]), str(row["length_band"]))].append(row)
    for queue in queues.values():
        queue.sort(key=lambda row: (str(row["stable_selection_hash"]), str(row["sample_id"])))

    joint_counts: Counter[tuple[str, str]] = Counter()
    ordered: list[dict[str, object]] = []
    script_rank = {name: index for index, name in enumerate(SCRIPT_ORDER)}
    length_rank = {name: index for index, name in enumerate(LENGTH_ORDER)}
    while any(queues.values()):
        available = [key for key, queue in queues.items() if queue]
        chosen = min(
            available,
            key=lambda key: (
                joint_counts[key],
                script_rank[key[0]],
                length_rank[key[1]],
                str(queues[key][0]["stable_selection_hash"]),
            ),
        )
        row = queues[chosen].pop(0)
        ordered.append(row)
        joint_counts[chosen] += 1
    return ordered


def select_candidates(units: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_label: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in units:
        by_label[int(row["label_id"])].append(row)
    selected: list[dict[str, object]] = []
    reserve: list[dict[str, object]] = []
    global_candidate = 0
    global_reserve = 0
    for label_id in LABELS:
        ordered = _ordered_from_strata(by_label[label_id])
        if len(ordered) < 20:
            raise ValueError(f"Label {label_id} has fewer than 20 eligible units")
        for within_rank, row in enumerate(ordered[:20], start=1):
            global_candidate += 1
            selected.append(
                {
                    "candidate_seed_index": global_candidate,
                    "sample_id": row["sample_id"],
                    "label_id": label_id,
                    "label_name": LABELS[label_id],
                    "phase0_split": "test",
                    "paraphrase_family_id": row["paraphrase_family_id"],
                    "family_size": row["family_size"],
                    "script_profile": row["script_profile"],
                    "length_band": row["length_band"],
                    "stable_selection_hash": row["stable_selection_hash"],
                    "selection_rank": within_rank,
                    "selection_status": "PENDING_HUMAN_REVIEW",
                }
            )
        for within_rank, row in enumerate(ordered[20:], start=1):
            global_reserve += 1
            reserve.append(
                {
                    "reserve_rank_global": global_reserve,
                    "reserve_rank_within_label": within_rank,
                    "sample_id": row["sample_id"],
                    "label_id": label_id,
                    "label_name": LABELS[label_id],
                    "paraphrase_family_id": row["paraphrase_family_id"],
                    "script_profile": row["script_profile"],
                    "length_band": row["length_band"],
                    "stable_selection_hash": row["stable_selection_hash"],
                }
            )
    return selected, reserve


def _coverage(rows: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {
        "overall": {
            "script_profiles": dict(sorted(Counter(str(row["script_profile"]) for row in rows).items())),
            "length_bands": dict(sorted(Counter(str(row["length_band"]) for row in rows).items())),
        },
        "per_label": [],
    }
    for label_id, label_name in LABELS.items():
        label_rows = [row for row in rows if int(row["label_id"]) == label_id]
        result["per_label"].append(
            {
                "label_id": label_id,
                "label_name": label_name,
                "count": len(label_rows),
                "script_profiles": dict(sorted(Counter(str(row["script_profile"]) for row in label_rows).items())),
                "length_bands": dict(sorted(Counter(str(row["length_band"]) for row in label_rows).items())),
            }
        )
    return result


def generate(
    source_path: Path,
    split_path: Path,
    family_path: Path,
    conflicts_path: Path,
    ontology_manifest_path: Path,
    protocol_manifest_path: Path,
    output_dir: Path,
    private_review_path: Path,
) -> dict[str, object]:
    units, texts = reconstruct_eligible_units(
        source_path, split_path, family_path, conflicts_path, ontology_manifest_path, protocol_manifest_path
    )
    candidates, reserve = select_candidates(units)
    candidate_path = output_dir / "challenge_seed_candidates_v1.csv"
    reserve_path = output_dir / "challenge_seed_reserve_order_v1.csv"
    profile_path = output_dir / "challenge_seed_candidate_profile_v1.json"
    manifest_path = output_dir / "challenge_seed_selection_manifest_v1.json"
    write_csv(candidate_path, CANDIDATE_FIELDS, candidates)
    write_csv(reserve_path, RESERVE_FIELDS, reserve)

    candidate_ids = {str(row["sample_id"]) for row in candidates}
    candidate_families = {str(row["paraphrase_family_id"]) for row in candidates}
    profile = {
        "benchmark_id": BENCHMARK_ID,
        "selection_version": SELECTION_VERSION,
        "status": "CANDIDATES_SELECTED",
        "candidate_count": len(candidates),
        "per_label_counts": {str(i): sum(int(row["label_id"]) == i for row in candidates) for i in LABELS},
        "coverage": _coverage(candidates),
        "unique_sample_ids": len(candidate_ids),
        "unique_families": len(candidate_families),
        "train_family_overlaps": 0,
        "dev_family_overlaps": 0,
        "source_conflict_seeds": 0,
        "duplicate_sample_ids": len(candidates) - len(candidate_ids),
        "final_seed_panel_frozen": False,
        "raw_text_emitted": False,
    }
    write_json(profile_path, profile)

    review_rows: list[dict[str, object]] = []
    for row in candidates:
        sample_id = str(row["sample_id"])
        review_rows.append(
            {
                "review_index": row["candidate_seed_index"],
                "sample_id": sample_id,
                "text": texts[sample_id],
                "source_label_id": row["label_id"],
                "source_label_name": row["label_name"],
                "canonical_label_id": row["label_id"],
                "canonical_label_name": row["label_name"],
                "phase0_split": "test",
                "paraphrase_family_id": row["paraphrase_family_id"],
                "script_profile": row["script_profile"],
                "length_band": row["length_band"],
                "classifiable": "",
                "explicit_enough": "",
                "transformable": "",
                "review_decision": "",
                "human_notes": "",
            }
        )
    write_csv(private_review_path, REVIEW_FIELDS, review_rows)

    manifest = {
        "benchmark_id": BENCHMARK_ID,
        "selection_version": SELECTION_VERSION,
        "starting_git_commit": STARTING_COMMIT,
        "phase0_source_sha256": sha256(source_path),
        "phase0_split_sha256": sha256(split_path),
        "family_map_sha256": sha256(family_path),
        "ontology_manifest_sha256": sha256(ontology_manifest_path),
        "challenge_protocol_manifest_sha256": sha256(protocol_manifest_path),
        "eligible_family_unit_counts": {str(key): value for key, value in EXPECTED_ELIGIBLE_FAMILIES.items()},
        "eligible_family_units": len(units),
        "candidate_panel_sha256": sha256(candidate_path),
        "reserve_order_sha256": sha256(reserve_path),
        "candidate_profile_sha256": sha256(profile_path),
        "private_review_queue_sha256": sha256(private_review_path),
        "target_candidates": 100,
        "target_per_label": 20,
        "unique_candidate_families": len(candidate_families),
        "reserve_rows": len(reserve),
        "selection_method": "DETERMINISTIC_FROZEN_PROTOCOL",
        "human_review_status": "PENDING",
        "final_seed_status": "NOT_FROZEN",
        "python_version": platform.python_version(),
        "raw_text_in_git_artifacts": False,
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    root = repository_root()
    private_root = root.parent / f"{root.name}_private"
    default_output = root / "research" / "phase1" / "challenge_benchmark"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=private_root / "phase0" / "nid_5class_source_v1.csv")
    parser.add_argument("--split-manifest", type=Path, default=root / "research" / "phase0" / "nid_5class_split_manifest_v1.csv")
    parser.add_argument("--family-map", type=Path, default=root / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv")
    parser.add_argument("--conflicts", type=Path, default=root / "research" / "phase1" / "ontology" / "nid_5class_source_conflicts_v1.csv")
    parser.add_argument("--ontology-manifest", type=Path, default=root / "research" / "phase1" / "ontology" / "nid_5class_ontology_manifest_v1.json")
    parser.add_argument("--protocol-manifest", type=Path, default=default_output / "challenge_protocol_manifest_v1.json")
    parser.add_argument("--output-dir", type=Path, default=default_output)
    parser.add_argument("--private-review", type=Path, default=private_root / "phase1" / "challenge_seed_review_queue_v1.csv")
    args = parser.parse_args()
    manifest = generate(
        args.source, args.split_manifest, args.family_map, args.conflicts,
        args.ontology_manifest, args.protocol_manifest, args.output_dir, args.private_review,
    )
    print("CHALLENGE SEED CANDIDATE SELECTION: PASS")
    print(f"ELIGIBLE FAMILY UNITS: {manifest['eligible_family_units']}")
    print(f"CANDIDATES: {manifest['target_candidates']}")
    print(f"RESERVE ROWS: {manifest['reserve_rows']}")
    print("HUMAN REVIEW STATUS: PENDING")
    print("FINAL SEED PANEL FROZEN: NO")


if __name__ == "__main__":
    main()
