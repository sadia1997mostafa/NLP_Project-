"""Build the deterministic final paraphrase-family map from Git-safe inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import platform
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PHASE0_MANIFEST = ROOT / "research/phase0/nid_5class_split_manifest_v1.csv"
FINAL_DECISIONS = HERE / "final_pair_decisions_v1.csv"
HUMAN_DECISIONS = HERE / "human_pair_decisions_v1.csv"
HUMAN_CONSISTENCY = HERE / "human_review_final_consistency_summary_v1.json"
FAMILY_MAP = HERE / "paraphrase_family_map_v1.csv"
FINAL_SUMMARY = HERE / "paraphrase_family_final_summary_v1.json"
FINAL_MANIFEST = HERE / "paraphrase_family_manifest_v1.json"

EXPECTED_PHASE0_SOURCE_SHA256 = (
    "6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa"
)
EXPECTED_PHASE0_MANIFEST_SHA256 = (
    "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
)
TASK1_COMMIT = "3ef30d868dc74325be0466c57f56a32b7929de2b"
TASK2_COMMIT = "d2eaae3c14533a3feda1f3eda23724ae9044a623"
VALIDATOR_COMMIT = "b961e4c8ae2aa12bb9d065198475faf420a0a51e"
TASK3_STARTING_COMMIT = VALIDATOR_COMMIT
EQUIVALENT = {"SAME_MEANING", "LABEL_CONFLICT_SAME_MEANING"}
ALLOWED_DECISIONS = {
    "SAME_MEANING",
    "SAME_TEMPLATE_DIFFERENT_MEANING",
    "RELATED_NOT_PARAPHRASE",
    "LABEL_CONFLICT_SAME_MEANING",
    "AMBIGUOUS_REVIEW_REQUIRED",
    "NOT_PARAPHRASE",
}
ALLOWED_SEMANTIC_SOURCES = {
    "human_confirmed",
    "codex_provisional",
}
ALLOWED_EQUIVALENCE = {"EQUIVALENT", "NOT_EQUIVALENT"}
ALLOWED_FAMILY_SOURCES = {
    "human_pair_review",
    "human_component_review",
    "codex_provisional",
}
EXPECTED_COMPONENT_REVIEW_SHA256 = (
    "267c1ae45eb8b5b3e9778be6a5c8902cd11f8feb5b5ccf04c9864bba92c5cadb"
)
EXPECTED_COMPONENT_PAIR_SHA256 = (
    "5f0306c505b00b396a4cae54255280e0d63d2faddb57477184abe2c90f649560"
)
MAP_COLUMNS = [
    "sample_id",
    "label_id",
    "label_name",
    "phase0_split",
    "paraphrase_family_id",
    "family_size",
    "family_status",
    "family_provenance",
]


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


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_inputs(
    phase0_manifest: Path,
    final_decisions: Path,
    human_decisions: Path,
    human_consistency: Path,
) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    dict[str, Any],
]:
    require(
        sha256_file(phase0_manifest) == EXPECTED_PHASE0_MANIFEST_SHA256,
        "Frozen Phase 0 manifest hash mismatch",
    )
    samples = read_csv(phase0_manifest)
    decisions = read_csv(final_decisions)
    human = read_csv(human_decisions)
    consistency = json.loads(human_consistency.read_text(encoding="utf-8"))

    require(len(samples) == 1454, "Expected 1454 Phase 0 samples")
    require(len({row["sample_id"] for row in samples}) == 1454, "Duplicate samples")
    require(len(decisions) == 99, "Expected 99 final pair decisions")
    require(len({row["pair_id"] for row in decisions}) == 99, "Duplicate pair IDs")
    require(len(human) == 29, "Expected 29 human decisions")
    require(len({row["pair_id"] for row in human}) == 29, "Duplicate human pair IDs")
    require(consistency["status"] == "PASS", "Final human consistency did not pass")
    require(
        consistency["mandatory_rereview_count"] == 0,
        "Unresolved mandatory human reviews",
    )

    sample_by_id = {row["sample_id"]: row for row in samples}
    for row in decisions:
        require(
            row["semantic_decision"] in ALLOWED_DECISIONS,
            "Invalid semantic decision",
        )
        require(
            row["semantic_decision_source"] in ALLOWED_SEMANTIC_SOURCES,
            "Invalid semantic decision source",
        )
        require(
            row["family_equivalence"] in ALLOWED_EQUIVALENCE,
            "Invalid family equivalence",
        )
        require(
            row["family_equivalence_source"] in ALLOWED_FAMILY_SOURCES,
            "Invalid family equivalence source",
        )
        require(
            row["sample_id_a"] in sample_by_id and row["sample_id_b"] in sample_by_id,
            "Unknown sample in final decisions",
        )
        require(
            row["label_a"] == sample_by_id[row["sample_id_a"]]["label_name"],
            f"Changed label for {row['sample_id_a']}",
        )
        require(
            row["label_b"] == sample_by_id[row["sample_id_b"]]["label_name"],
            f"Changed label for {row['sample_id_b']}",
        )
        require(
            not (
                row["label_a"] != row["label_b"]
                and row["semantic_decision"] == "SAME_MEANING"
            ),
            f"Cross-label SAME_MEANING violation: {row['pair_id']}",
        )
    sources = Counter(row["semantic_decision_source"] for row in decisions)
    require(
        sources
        == {"human_confirmed": 29, "codex_provisional": 70},
        "Final semantic provenance counts mismatch",
    )
    human_ids = {row["pair_id"] for row in human}
    require(
        human_ids
        == {
            row["pair_id"]
            for row in decisions
            if row["semantic_decision_source"] == "human_confirmed"
        },
        "Human decision IDs differ from final decisions",
    )
    return samples, decisions, human, consistency


def construct_family_map(
    samples: list[dict[str, str]],
    decisions: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sample_by_id = {row["sample_id"]: row for row in samples}
    parent = {sample_id: sample_id for sample_id in sample_by_id}

    def find(sample_id: str) -> str:
        while parent[sample_id] != sample_id:
            parent[sample_id] = parent[parent[sample_id]]
            sample_id = parent[sample_id]
        return sample_id

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    decision_by_pair: dict[tuple[str, str], dict[str, str]] = {}
    for row in decisions:
        key = tuple(sorted((row["sample_id_a"], row["sample_id_b"])))
        require(key not in decision_by_pair, "Symmetric or duplicate pair decision")
        decision_by_pair[key] = row
        if row["family_equivalence"] == "EQUIVALENT":
            union(row["sample_id_a"], row["sample_id_b"])

    components: dict[str, list[str]] = defaultdict(list)
    for sample_id in sorted(sample_by_id):
        components[find(sample_id)].append(sample_id)
    ordered = sorted(components.values(), key=lambda members: min(members))

    family_rows: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []
    for number, members in enumerate(ordered, start=1):
        family_id = f"NID5-PF-FINAL-{number:04d}"
        member_set = set(members)
        labels = {sample_by_id[sample_id]["label_name"] for sample_id in members}
        splits = {sample_by_id[sample_id]["split"] for sample_id in members}
        component_edges = [
            row
            for row in decisions
            if row["sample_id_a"] in member_set
            and row["sample_id_b"] in member_set
            and row["family_equivalence"] == "EQUIVALENT"
        ]

        if len(members) > 1:
            for left, right in itertools.combinations(members, 2):
                represented = decision_by_pair.get(tuple(sorted((left, right))))
                if (
                    represented
                    and represented["family_equivalence"] == "NOT_EQUIVALENT"
                ):
                    raise ValueError(
                        "FINAL FAMILY CONSISTENCY FAILURE: "
                        f"{family_id} contains contradictory pair "
                        f"{represented['pair_id']}"
                    )
            require(component_edges, f"Multi-row family lacks edges: {family_id}")
            edge_sources = {
                row["family_equivalence_source"] for row in component_edges
            }
            human_sources = {"human_pair_review", "human_component_review"}
            if edge_sources.issubset(human_sources):
                provenance = "human_reviewed_component"
            elif edge_sources == {"codex_provisional"}:
                provenance = "codex_high_confidence_component"
            else:
                provenance = "mixed_human_codex_component"
            status = (
                "LABEL_CONFLICT_FAMILY"
                if len(labels) > 1
                else "CONFIRMED_MULTIROW"
            )
        else:
            provenance = "singleton"
            status = "SINGLETON"

        for sample_id in members:
            sample = sample_by_id[sample_id]
            family_rows.append(
                {
                    "sample_id": sample_id,
                    "label_id": sample["label_id"],
                    "label_name": sample["label_name"],
                    "phase0_split": sample["split"],
                    "paraphrase_family_id": family_id,
                    "family_size": len(members),
                    "family_status": status,
                    "family_provenance": provenance,
                }
            )
        metadata.append(
            {
                "family_id": family_id,
                "size": len(members),
                "labels": labels,
                "splits": splits,
                "status": status,
                "provenance": provenance,
            }
        )

    multi = [item for item in metadata if item["size"] > 1]
    cross_split = [item for item in multi if len(item["splits"]) > 1]
    stats = {
        "total_samples": len(family_rows),
        "total_families": len(metadata),
        "multi_row_families": len(multi),
        "singleton_families": sum(item["size"] == 1 for item in metadata),
        "largest_family_size": max(item["size"] for item in metadata),
        "label_conflict_families": sum(
            item["status"] == "LABEL_CONFLICT_FAMILY" for item in multi
        ),
        "families_with_human_confirmed_edge": sum(
            item["provenance"]
            in {"human_reviewed_component", "mixed_human_codex_component"}
            for item in multi
        ),
        "human_reviewed_components": sum(
            item["provenance"] == "human_reviewed_component" for item in multi
        ),
        "codex_only_components": sum(
            item["provenance"] == "codex_high_confidence_component"
            for item in multi
        ),
        "mixed_provenance_components": sum(
            item["provenance"] == "mixed_human_codex_component" for item in multi
        ),
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
        "samples_affected_by_cross_split_families": sum(
            item["size"] for item in cross_split
        ),
        "same_label_cross_split_families": sum(
            len(item["labels"]) == 1 for item in cross_split
        ),
        "cross_label_cross_split_families": sum(
            len(item["labels"]) > 1 for item in cross_split
        ),
    }
    require(stats["total_samples"] == 1454, "Family map must contain 1454 samples")
    return sorted(family_rows, key=lambda row: row["sample_id"]), stats


def build_final(
    phase0_manifest: Path,
    final_decisions_path: Path,
    human_decisions_path: Path,
    human_consistency_path: Path,
    family_map_path: Path,
    summary_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    samples, decisions, human, consistency = load_inputs(
        phase0_manifest,
        final_decisions_path,
        human_decisions_path,
        human_consistency_path,
    )
    family_rows, family_stats = construct_family_map(samples, decisions)
    write_csv(family_map_path, family_rows, MAP_COLUMNS)

    decision_distribution = dict(
        sorted(Counter(row["semantic_decision"] for row in decisions).items())
    )
    equivalence_distribution = dict(
        sorted(Counter(row["family_equivalence"] for row in decisions).items())
    )
    summary = {
        "candidate_pairs": 99,
        "targeted_pair_human_reviews": 29,
        "machine_assisted_candidate_pairs": 70,
        "human_correction_count": 1,
        "corrected_pair": "NID5-ND-000048",
        "human_component_reviews": 1,
        "component_samples_reviewed": 4,
        "component_pair_relations": 6,
        "final_human_review_sha256": consistency["final_private_review_sha256"],
        "human_correction_queue_sha256": consistency[
            "human_correction_queue_sha256"
        ],
        "component_review_sha256": EXPECTED_COMPONENT_REVIEW_SHA256,
        "component_pair_derivation_sha256": EXPECTED_COMPONENT_PAIR_SHA256,
        "human_pair_decisions_sha256": sha256_file(human_decisions_path),
        "final_pair_decisions_sha256": sha256_file(final_decisions_path),
        "family_map_sha256": sha256_file(family_map_path),
        "decision_distribution": decision_distribution,
        "family_equivalence_distribution": equivalence_distribution,
        "family_statistics": family_stats,
        "provisional_comparison": {
            "provisional_total_families": 1408,
            "final_total_families": family_stats["total_families"],
            "provisional_multi_row_families": 42,
            "final_multi_row_families": family_stats["multi_row_families"],
            "provisional_singleton_families": 1366,
            "final_singleton_families": family_stats["singleton_families"],
            "provisional_largest_family_size": 4,
            "final_largest_family_size": family_stats["largest_family_size"],
            "provisional_cross_split_affected_samples": 33,
            "final_cross_split_affected_samples": family_stats[
                "samples_affected_by_cross_split_families"
            ],
        },
        "cross_split_statistics": {
            key: family_stats[key]
            for key in (
                "train_dev_families",
                "train_test_families",
                "dev_test_families",
                "families_crossing_more_than_two_splits",
                "samples_affected_by_cross_split_families",
                "same_label_cross_split_families",
                "cross_label_cross_split_families",
            )
        },
        "label_conflict_statistics": {
            "families": family_stats["label_conflict_families"],
            "source_labels_changed": False,
        },
        "final_family_status": "FROZEN",
        "annotation_status": "TARGETED_HUMAN_REVIEW_WITH_MACHINE_ASSISTANCE",
        "annotation_scope": (
            "29 high-risk/ambiguous pairs human reviewed; remaining 70 "
            "retained as machine-assisted decisions"
        ),
        "fully_human_annotated": False,
        "unresolved_mandatory_reviews": 0,
        "transitive_consistency": "PASS",
    }
    write_json(summary_path, summary)

    manifest = {
        "protocol": "NID-5CLASS-PHASE1-PARAPHRASE-FAMILY-V1",
        "phase0_source_sha256": EXPECTED_PHASE0_SOURCE_SHA256,
        "phase0_split_manifest_sha256": EXPECTED_PHASE0_MANIFEST_SHA256,
        "task1_leakage_audit_commit": TASK1_COMMIT,
        "task2_provisional_family_commit": TASK2_COMMIT,
        "human_review_validator_commit": VALIDATOR_COMMIT,
        "final_private_human_review_sha256": summary[
            "final_human_review_sha256"
        ],
        "human_correction_queue_sha256": summary[
            "human_correction_queue_sha256"
        ],
        "component_review_sha256": EXPECTED_COMPONENT_REVIEW_SHA256,
        "component_pair_derivation_sha256": EXPECTED_COMPONENT_PAIR_SHA256,
        "human_pair_decisions_sha256": summary[
            "human_pair_decisions_sha256"
        ],
        "final_pair_decisions_sha256": summary[
            "final_pair_decisions_sha256"
        ],
        "family_map_sha256": summary["family_map_sha256"],
        "python_version": platform.python_version(),
        "builder_script": str(
            Path("research/phase1/paraphrase_families/build_final_families.py")
        ),
        "git_starting_commit": TASK3_STARTING_COMMIT,
        "raw_text_in_git_outputs": False,
    }
    write_json(manifest_path, manifest)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the deterministic final Phase 1 paraphrase-family map."
    )
    parser.add_argument("--phase0-manifest", type=Path, default=PHASE0_MANIFEST)
    parser.add_argument("--final-decisions", type=Path, default=FINAL_DECISIONS)
    parser.add_argument("--human-decisions", type=Path, default=HUMAN_DECISIONS)
    parser.add_argument("--human-consistency", type=Path, default=HUMAN_CONSISTENCY)
    parser.add_argument("--family-map", type=Path, default=FAMILY_MAP)
    parser.add_argument("--summary", type=Path, default=FINAL_SUMMARY)
    parser.add_argument("--manifest", type=Path, default=FINAL_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_final(
        args.phase0_manifest,
        args.final_decisions,
        args.human_decisions,
        args.human_consistency,
        args.family_map,
        args.summary,
        args.manifest,
    )
    stats = summary["family_statistics"]
    print("FINAL FAMILY BUILD: PASS")
    print("SAMPLES:", stats["total_samples"])
    print("FAMILIES:", stats["total_families"])
    print("MULTI-ROW:", stats["multi_row_families"])
    print("SINGLETON:", stats["singleton_families"])
    print("FAMILY MAP SHA-256:", summary["family_map_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
