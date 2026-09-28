"""Build a private, deterministic evidence sample for the five-class audit.

Raw query text is written only to the external private research directory.
The output is evidence for human/semantic inspection, not a relabelled dataset.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


FROZEN_LABELS = {
    0: "NID Information Correction",
    1: "New NID Registration",
    2: "Lost/Stolen NID",
    3: "NID Online Problem",
    4: "Smart ID Card",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_private_output(root: Path) -> Path:
    return root.parent / f"{root.name}_private" / "phase1" / "label_definition_evidence_v1.csv"


def default_boundary_output(root: Path) -> Path:
    return root.parent / f"{root.name}_private" / "phase1" / "label_boundary_review_queue_v1.csv"


def build_evidence(source: Path, manifest: Path, family_map: Path, pairs: Path) -> pd.DataFrame:
    source_frame = pd.read_csv(source).reset_index(drop=True)
    source_frame["source_row_number"] = source_frame.index + 1
    manifest_frame = pd.read_csv(manifest)
    families = pd.read_csv(family_map)
    decisions = pd.read_csv(pairs)

    if len(source_frame) != 1454 or len(manifest_frame) != 1454:
        raise ValueError("Frozen source/manifest row count mismatch")
    if set(manifest_frame["label_name"]) != set(FROZEN_LABELS.values()):
        raise ValueError("Frozen label inventory mismatch")

    frame = manifest_frame.merge(
        source_frame[["source_row_number", "text", "problem", "language_style", "difficulty"]],
        on="source_row_number",
        validate="one_to_one",
    ).merge(
        families[["sample_id", "paraphrase_family_id", "family_status"]],
        on="sample_id",
        validate="one_to_one",
    )
    if not (frame["problem"] == frame["label_name"]).all():
        raise ValueError("Source labels do not match the frozen manifest")

    reasons: dict[str, set[str]] = {sample_id: set() for sample_id in frame["sample_id"]}
    cross_label = decisions[decisions["label_a"] != decisions["label_b"]]
    for row in cross_label.itertuples(index=False):
        reasons[row.sample_id_a].add("cross_label_boundary_pair")
        reasons[row.sample_id_b].add("cross_label_boundary_pair")
        if row.family_equivalence == "EQUIVALENT":
            reasons[row.sample_id_a].add("label_conflict_family")
            reasons[row.sample_id_b].add("label_conflict_family")

    for label_id, label_name in FROZEN_LABELS.items():
        group = frame[frame["label_name"] == label_name].sort_values("source_row_number")
        # Evenly spaced coverage avoids selecting only easy or adjacent rows.
        for index in np.linspace(0, len(group) - 1, 12, dtype=int):
            reasons[group.iloc[index]["sample_id"]].add("systematic_coverage")
        lengths = group["text"].fillna("").astype(str).str.len()
        for index in lengths.nsmallest(4).index:
            reasons[group.loc[index, "sample_id"]].add("short_or_underspecified")
        for index in lengths.nlargest(3).index:
            reasons[group.loc[index, "sample_id"]].add("unusual_long_form")
        for style, style_group in group.groupby("language_style", dropna=False):
            for sample_id in style_group.sort_values("source_row_number").head(3)["sample_id"]:
                reasons[sample_id].add(f"language_style_{style}")

    selected = frame[frame["sample_id"].map(lambda value: bool(reasons[value]))].copy()
    selected["evidence_categories"] = selected["sample_id"].map(
        lambda value: "|".join(sorted(reasons[value]))
    )
    selected = selected.sort_values(["label_id", "source_row_number"]).reset_index(drop=True)
    selected.insert(0, "evidence_id", [f"NID5-EV-{number:04d}" for number in range(1, len(selected) + 1)])
    return selected[
        [
            "evidence_id",
            "sample_id",
            "text",
            "label_id",
            "label_name",
            "split",
            "language_style",
            "difficulty",
            "evidence_categories",
            "paraphrase_family_id",
            "family_status",
        ]
    ]


def build_boundary_queue(source: Path, manifest: Path, pairs: Path) -> pd.DataFrame:
    source_frame = pd.read_csv(source).reset_index(drop=True)
    source_frame["source_row_number"] = source_frame.index + 1
    manifest_frame = pd.read_csv(manifest)
    frame = manifest_frame.merge(
        source_frame[["source_row_number", "text"]], on="source_row_number", validate="one_to_one"
    ).set_index("sample_id")
    decisions = pd.read_csv(pairs)
    conflicts = decisions[
        (decisions["label_a"] != decisions["label_b"])
        & (decisions["family_equivalence"] == "EQUIVALENT")
    ]
    rows: dict[str, dict[str, str]] = {}
    for pair in conflicts.itertuples(index=False):
        for sample_id, source_label, candidate in (
            (pair.sample_id_a, pair.label_a, pair.label_b),
            (pair.sample_id_b, pair.label_b, pair.label_a),
        ):
            entry = rows.setdefault(
                sample_id,
                {
                    "sample_id": sample_id,
                    "text": str(frame.loc[sample_id, "text"]),
                    "source_label": source_label,
                    "candidate_label_a": source_label,
                    "candidate_label_b": candidate,
                    "reason_for_review": "cross-label equivalent family",
                    "provisional_boundary_issue": "source label conflicts with a semantically equivalent sample carrying another frozen label",
                    "human_decision": "",
                    "human_notes": "",
                },
            )
            if candidate not in {entry["candidate_label_a"], entry["candidate_label_b"]}:
                entry["candidate_label_b"] = candidate
    queue = pd.DataFrame(sorted(rows.values(), key=lambda item: item["sample_id"]))
    queue.insert(0, "review_id", [f"NID5-BR-{number:04d}" for number in range(1, len(queue) + 1)])
    return queue


def main() -> None:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=root.parent / f"{root.name}_private" / "phase0" / "nid_5class_source_v1.csv")
    parser.add_argument("--manifest", type=Path, default=root / "research" / "phase0" / "nid_5class_split_manifest_v1.csv")
    parser.add_argument("--family-map", type=Path, default=root / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv")
    parser.add_argument("--pair-decisions", type=Path, default=root / "research" / "phase1" / "paraphrase_families" / "final_pair_decisions_v1.csv")
    parser.add_argument("--output", type=Path, default=default_private_output(root))
    parser.add_argument("--boundary-output", type=Path, default=default_boundary_output(root))
    args = parser.parse_args()

    evidence = build_evidence(args.source, args.manifest, args.family_map, args.pair_decisions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    evidence.to_csv(args.output, index=False, encoding="utf-8")
    queue = build_boundary_queue(args.source, args.manifest, args.pair_decisions)
    args.boundary_output.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(args.boundary_output, index=False, encoding="utf-8")
    print(f"PRIVATE EVIDENCE ROWS: {len(evidence)}")
    print(f"PRIVATE EVIDENCE PATH: {args.output}")
    print(f"PRIVATE EVIDENCE SHA-256: {sha256(args.output)}")
    print("LABEL COUNTS:")
    print(evidence.groupby(["label_id", "label_name"]).size().to_string())
    print(f"PRIVATE BOUNDARY REVIEW ROWS: {len(queue)}")
    print(f"PRIVATE BOUNDARY REVIEW PATH: {args.boundary_output}")
    print(f"PRIVATE BOUNDARY REVIEW SHA-256: {sha256(args.boundary_output)}")


if __name__ == "__main__":
    main()
