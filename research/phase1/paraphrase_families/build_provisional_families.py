"""Build deterministic provisional families from already-adjudicated pairs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIVATE_ROOT = ROOT.parent / f"{ROOT.name}_private" / "phase1"
EQUIVALENT = {"SAME_MEANING", "LABEL_CONFLICT_SAME_MEANING"}
DECISIONS = {
    "SAME_MEANING",
    "SAME_TEMPLATE_DIFFERENT_MEANING",
    "RELATED_NOT_PARAPHRASE",
    "LABEL_CONFLICT_SAME_MEANING",
    "AMBIGUOUS_REVIEW_REQUIRED",
    "NOT_PARAPHRASE",
}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
FAMILY_STATUS = {
    "PROVISIONAL_CONFIRMED",
    "SINGLETON",
    "HUMAN_REVIEW_REQUIRED",
    "LABEL_CONFLICT",
}
EXPECTED_PHASE0_MANIFEST_SHA256 = (
    "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
)
EXPECTED_PAIR_COUNT = 99
MAP_COLUMNS = [
    "sample_id",
    "label_id",
    "label_name",
    "phase0_split",
    "provisional_family_id",
    "family_size",
    "family_status",
    "adjudication_source",
]
INDEX_COLUMNS = [
    "review_id",
    "pair_id",
    "sample_id_a",
    "sample_id_b",
    "label_a",
    "label_b",
    "split_a",
    "split_b",
    "similarity",
    "codex_provisional_decision",
    "codex_confidence",
    "reason_for_human_review",
]
PRIVATE_ADJUDICATED_COLUMNS = [
    "pair_id",
    "sample_id_a",
    "text_a",
    "label_a",
    "split_a",
    "sample_id_b",
    "text_b",
    "label_b",
    "split_b",
    "char_tfidf_cosine",
    "token_jaccard",
    "sequence_similarity",
    "provisional_decision",
    "confidence",
    "reason_code",
    "short_private_note",
    "adjudication_source",
]
PRIVATE_QUEUE_COLUMNS = [
    "review_id",
    "pair_id",
    "sample_id_a",
    "text_a",
    "label_a",
    "split_a",
    "sample_id_b",
    "text_b",
    "label_b",
    "split_b",
    "similarity",
    "codex_provisional_decision",
    "codex_confidence",
    "codex_reason_code",
    "human_decision",
    "human_notes",
]
NOTE_BY_REASON = {
    "EXACT_EQUIVALENCE": "Texts express the same request exactly.",
    "SPELLING_VARIANT": "Meaning is unchanged by spelling variation.",
    "SCRIPT_VARIANT": "Meaning is unchanged across script or language form.",
    "WORD_ORDER_VARIANT": "Wording differs but the requested information is the same.",
    "SLOT_VARIANT_SAME_INTENT": "A minor slot differs while the requested action remains the same.",
    "SAME_FRAME_DIFFERENT_SLOT_MEANING": "The shared frame targets a different field, object, or workflow.",
    "DIFFERENT_SERVICE_ACTION": "The requested citizen action differs.",
    "BROADER_VS_NARROWER": "One request is broader or asks a different level of detail.",
    "RELATED_CONCEPT": "The topics are related but require distinguishable answers.",
    "SOURCE_LABEL_CONFLICT": "Equivalent meaning appears under different frozen labels.",
    "INSUFFICIENT_CONTEXT": "Equivalence is likely but one query omits useful context.",
    "LEXICAL_FALSE_POSITIVE": "Surface overlap does not preserve meaning.",
    "OTHER": "Provisional semantic judgment requires review.",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_contracts(
    phase0_manifest: Path,
    decisions_path: Path,
    task1_pairs_path: Path,
    private_review_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    require(
        sha256_file(phase0_manifest) == EXPECTED_PHASE0_MANIFEST_SHA256,
        "Frozen Phase 0 manifest hash mismatch",
    )
    samples = read_csv(phase0_manifest)
    require(len(samples) == 1454, "Expected 1454 Phase 0 samples")
    require(len({row["sample_id"] for row in samples}) == 1454, "Sample IDs are not unique")
    decisions = read_csv(decisions_path)
    require(len(decisions) == EXPECTED_PAIR_COUNT, "Expected 99 pair decisions")
    require(len({row["pair_id"] for row in decisions}) == EXPECTED_PAIR_COUNT, "Pair IDs are not unique")
    require({row["provisional_decision"] for row in decisions}.issubset(DECISIONS), "Invalid decision")
    require({row["confidence"] for row in decisions}.issubset(CONFIDENCE), "Invalid confidence")
    require(
        {row["adjudication_source"] for row in decisions} == {"codex_provisional"},
        "Adjudication source must be codex_provisional",
    )
    pairs = {row["pair_id"]: row for row in read_csv(task1_pairs_path)}
    private = {row["pair_id"]: row for row in read_csv(private_review_path)}
    require(set(pairs) == set(private) == {row["pair_id"] for row in decisions}, "Pair sources differ")
    return samples, decisions, pairs, private


def construct_families(
    samples: list[dict[str, str]], decisions: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    sample_by_id = {row["sample_id"]: row for row in samples}
    parent = {sample_id: sample_id for sample_id in sample_by_id}

    def find(sample_id: str) -> str:
        while parent[sample_id] != sample_id:
            parent[sample_id] = parent[parent[sample_id]]
            sample_id = parent[sample_id]
        return sample_id

    def union(left: str, right: str) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[max(root_left, root_right)] = min(root_left, root_right)

    decision_by_pair = {}
    equivalence_edges = []
    for row in decisions:
        left, right = row["sample_id_a"], row["sample_id_b"]
        require(left in sample_by_id and right in sample_by_id, "Unknown sample in decisions")
        key = tuple(sorted((left, right)))
        decision_by_pair[key] = row["provisional_decision"]
        if row["provisional_decision"] in EQUIVALENT:
            equivalence_edges.append(row)
            union(left, right)

    components: dict[str, list[str]] = defaultdict(list)
    for sample_id in sorted(sample_by_id):
        components[find(sample_id)].append(sample_id)
    ordered_components = sorted(components.values(), key=lambda members: min(members))
    family_rows = []
    sample_status = {}
    component_metadata = []
    for number, members in enumerate(ordered_components, start=1):
        family_id = f"NID5-PF-V1-{number:04d}"
        labels = {sample_by_id[sample_id]["label_name"] for sample_id in members}
        splits = {sample_by_id[sample_id]["split"] for sample_id in members}
        unsafe_transitivity = False
        if len(members) > 2:
            for left, right in itertools.combinations(members, 2):
                if decision_by_pair.get(tuple(sorted((left, right)))) not in EQUIVALENT:
                    unsafe_transitivity = True
                    break
        if len(members) == 1:
            status = "SINGLETON"
        elif unsafe_transitivity:
            status = "HUMAN_REVIEW_REQUIRED"
        elif len(labels) > 1:
            status = "LABEL_CONFLICT"
        else:
            status = "PROVISIONAL_CONFIRMED"
        require(status in FAMILY_STATUS, "Invalid family status")
        for sample_id in members:
            sample = sample_by_id[sample_id]
            family_rows.append(
                {
                    "sample_id": sample_id,
                    "label_id": sample["label_id"],
                    "label_name": sample["label_name"],
                    "phase0_split": sample["split"],
                    "provisional_family_id": family_id,
                    "family_size": len(members),
                    "family_status": status,
                    "adjudication_source": "codex_provisional",
                }
            )
            sample_status[sample_id] = status
        component_metadata.append(
            {
                "family_id": family_id,
                "members": members,
                "size": len(members),
                "labels": labels,
                "splits": splits,
                "status": status,
            }
        )

    multi = [item for item in component_metadata if item["size"] > 1]
    cross_split = [item for item in multi if len(item["splits"]) > 1]
    statistics = {
        "equivalence_edge_count": len(equivalence_edges),
        "total_families": len(component_metadata),
        "multi_row_families": len(multi),
        "singleton_families": sum(item["size"] == 1 for item in component_metadata),
        "largest_family_size": max(item["size"] for item in component_metadata),
        "review_required_families": sum(
            item["status"] == "HUMAN_REVIEW_REQUIRED" for item in component_metadata
        ),
        "label_conflict_families": sum(
            item["status"] == "LABEL_CONFLICT" for item in component_metadata
        ),
        "cross_label_families": sum(len(item["labels"]) > 1 for item in multi),
        "train_dev_families": sum(
            {"train", "dev"}.issubset(item["splits"]) for item in multi
        ),
        "train_test_families": sum(
            {"train", "test"}.issubset(item["splits"]) for item in multi
        ),
        "dev_test_families": sum(
            {"dev", "test"}.issubset(item["splits"]) for item in multi
        ),
        "families_crossing_more_than_two_splits": sum(
            len(item["splits"]) > 2 for item in multi
        ),
        "samples_affected_by_cross_split_families": sum(item["size"] for item in cross_split),
        "same_label_cross_split_families": sum(
            len(item["labels"]) == 1 for item in cross_split
        ),
        "cross_label_cross_split_families": sum(
            len(item["labels"]) > 1 for item in cross_split
        ),
    }
    return sorted(family_rows, key=lambda row: row["sample_id"]), statistics, sample_status


def create_private_outputs(
    decisions: list[dict[str, str]],
    pairs: dict[str, dict[str, str]],
    private: dict[str, dict[str, str]],
    sample_status: dict[str, str],
    adjudicated_output: Path,
    queue_output: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    require(not adjudicated_output.resolve().is_relative_to(ROOT.resolve()), "Private adjudication must be outside Git")
    require(not queue_output.resolve().is_relative_to(ROOT.resolve()), "Private queue must be outside Git")
    decision_by_id = {row["pair_id"]: row for row in decisions}
    adjudicated = []
    queue_rows = []
    queue_index = []
    for row in decisions:
        pair_id = row["pair_id"]
        raw = private[pair_id]
        pair = pairs[pair_id]
        adjudicated.append(
            {
                "pair_id": pair_id,
                "sample_id_a": row["sample_id_a"],
                "text_a": raw["text_a"],
                "label_a": row["label_a"],
                "split_a": row["split_a"],
                "sample_id_b": row["sample_id_b"],
                "text_b": raw["text_b"],
                "label_b": row["label_b"],
                "split_b": row["split_b"],
                "char_tfidf_cosine": row["char_tfidf_cosine"],
                "token_jaccard": raw["token_jaccard"],
                "sequence_similarity": raw["sequence_similarity"],
                "provisional_decision": row["provisional_decision"],
                "confidence": row["confidence"],
                "reason_code": row["reason_code"],
                "short_private_note": NOTE_BY_REASON[row["reason_code"]],
                "adjudication_source": "codex_provisional",
            }
        )
        reasons = []
        if row["confidence"] != "HIGH":
            reasons.append("NON_HIGH_CONFIDENCE")
        if row["provisional_decision"] == "AMBIGUOUS_REVIEW_REQUIRED":
            reasons.append("AMBIGUOUS_DECISION")
        if row["provisional_decision"] == "LABEL_CONFLICT_SAME_MEANING":
            reasons.append("LABEL_CONFLICT_EQUIVALENCE")
        if row["label_a"] != row["label_b"] and row["provisional_decision"] == "SAME_MEANING":
            reasons.append("CROSS_LABEL_SAME_MEANING")
        if (
            sample_status[row["sample_id_a"]] == "HUMAN_REVIEW_REQUIRED"
            or sample_status[row["sample_id_b"]] == "HUMAN_REVIEW_REQUIRED"
        ):
            reasons.append("FAMILY_REVIEW_REQUIRED")
        if (
            row["split_a"] != row["split_b"]
            and float(row["char_tfidf_cosine"]) >= 0.90
            and not (
                row["provisional_decision"] == "NOT_PARAPHRASE"
                and row["confidence"] == "HIGH"
            )
        ):
            reasons.append("HIGH_SIMILARITY_CROSS_SPLIT")
        if (
            pair["normalized_hash_equality"].lower() == "true"
            and row["label_a"] != row["label_b"]
        ):
            reasons.append("EXACT_CROSS_LABEL_CONFLICT")
        if reasons:
            review_id = f"NID5-HR-V1-{len(queue_rows) + 1:04d}"
            queue_rows.append(
                {
                    "review_id": review_id,
                    "pair_id": pair_id,
                    "sample_id_a": row["sample_id_a"],
                    "text_a": raw["text_a"],
                    "label_a": row["label_a"],
                    "split_a": row["split_a"],
                    "sample_id_b": row["sample_id_b"],
                    "text_b": raw["text_b"],
                    "label_b": row["label_b"],
                    "split_b": row["split_b"],
                    "similarity": row["char_tfidf_cosine"],
                    "codex_provisional_decision": row["provisional_decision"],
                    "codex_confidence": row["confidence"],
                    "codex_reason_code": row["reason_code"],
                    "human_decision": "",
                    "human_notes": "",
                }
            )
            queue_index.append(
                {
                    "review_id": review_id,
                    "pair_id": pair_id,
                    "sample_id_a": row["sample_id_a"],
                    "sample_id_b": row["sample_id_b"],
                    "label_a": row["label_a"],
                    "label_b": row["label_b"],
                    "split_a": row["split_a"],
                    "split_b": row["split_b"],
                    "similarity": row["char_tfidf_cosine"],
                    "codex_provisional_decision": row["provisional_decision"],
                    "codex_confidence": row["confidence"],
                    "reason_for_human_review": ";".join(reasons),
                }
            )
    write_csv(adjudicated_output, adjudicated, PRIVATE_ADJUDICATED_COLUMNS)
    write_csv(queue_output, queue_rows, PRIVATE_QUEUE_COLUMNS)
    return queue_index, queue_rows


def build_all(
    phase0_manifest: Path,
    decisions_path: Path,
    task1_pairs_path: Path,
    private_review_path: Path,
    output_dir: Path,
    adjudicated_output: Path,
    queue_output: Path,
) -> dict[str, Any]:
    samples, decisions, pairs, private = load_contracts(
        phase0_manifest, decisions_path, task1_pairs_path, private_review_path
    )
    family_rows, family_stats, sample_status = construct_families(samples, decisions)
    require(len(family_rows) == 1454, "Family map must contain 1454 rows")
    require(len({row["sample_id"] for row in family_rows}) == 1454, "Duplicate family-map sample")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "provisional_paraphrase_family_map_v1.csv", family_rows, MAP_COLUMNS)
    queue_index, queue_rows = create_private_outputs(
        decisions,
        pairs,
        private,
        sample_status,
        adjudicated_output,
        queue_output,
    )
    write_csv(output_dir / "human_review_queue_index_v1.csv", queue_index, INDEX_COLUMNS)
    decision_counts = dict(sorted(Counter(row["provisional_decision"] for row in decisions).items()))
    confidence_counts = dict(sorted(Counter(row["confidence"] for row in decisions).items()))
    decision_by_label = {
        decision: dict(
            sorted(
                Counter(
                    "same_label" if row["label_a"] == row["label_b"] else "cross_label"
                    for row in decisions
                    if row["provisional_decision"] == decision
                ).items()
            )
        )
        for decision in sorted(DECISIONS)
    }
    decision_by_split = {
        decision: dict(
            sorted(
                Counter(
                    "same_split" if row["split_a"] == row["split_b"] else "cross_split"
                    for row in decisions
                    if row["provisional_decision"] == decision
                ).items()
            )
        )
        for decision in sorted(DECISIONS)
    }
    summary = {
        "source_row_count": 1454,
        "candidate_pair_count": len(decisions),
        "decision_counts": decision_counts,
        "confidence_counts": confidence_counts,
        "decision_by_label_relation": decision_by_label,
        "decision_by_split_relation": decision_by_split,
        "family_statistics": family_stats,
        "human_review_queue_size": len(queue_rows),
        "private_adjudicated_file": {
            "path": str(adjudicated_output.resolve()),
            "sha256": sha256_file(adjudicated_output),
            "rows": len(decisions),
        },
        "private_human_review_queue": {
            "path": str(queue_output.resolve()),
            "sha256": sha256_file(queue_output),
            "rows": len(queue_rows),
        },
        "adjudication_source": "codex_provisional",
        "final_human_adjudication_status": "PENDING",
        "labels_changed": False,
        "phase0_split_changed": False,
        "model_evaluations": 0,
    }
    write_json(output_dir / "paraphrase_family_summary_v1.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build provisional family assignments from semantic pair decisions."
    )
    parser.add_argument(
        "--phase0-manifest",
        type=Path,
        default=ROOT / "research/phase0/nid_5class_split_manifest_v1.csv",
    )
    parser.add_argument(
        "--pair-decisions", type=Path,
        default=HERE / "provisional_pair_decisions_v1.csv",
    )
    parser.add_argument(
        "--task1-pairs", type=Path,
        default=ROOT / "research/phase1/leakage_audit/near_duplicate_pairs_v1.csv",
    )
    parser.add_argument(
        "--private-review-input", type=Path,
        default=PRIVATE_ROOT / "near_duplicate_review_v1.csv",
    )
    parser.add_argument("--output-dir", type=Path, default=HERE)
    parser.add_argument(
        "--private-adjudicated-output", type=Path,
        default=PRIVATE_ROOT / "near_duplicate_review_v1_adjudicated.csv",
    )
    parser.add_argument(
        "--private-queue-output", type=Path,
        default=PRIVATE_ROOT / "human_review_queue_v1.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_all(
        args.phase0_manifest,
        args.pair_decisions,
        args.task1_pairs,
        args.private_review_input,
        args.output_dir,
        args.private_adjudicated_output,
        args.private_queue_output,
    )
    print("PROVISIONAL FAMILY BUILD: PASS")
    print("SAMPLES:", summary["source_row_count"])
    print("PAIR DECISIONS:", summary["candidate_pair_count"])
    print("MULTI-ROW FAMILIES:", summary["family_statistics"]["multi_row_families"])
    print("SINGLETON FAMILIES:", summary["family_statistics"]["singleton_families"])
    print("HUMAN REVIEW QUEUE:", summary["human_review_queue_size"])


if __name__ == "__main__":
    main()
