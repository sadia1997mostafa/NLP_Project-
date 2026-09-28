"""Apply the single approved human correction and freeze safe decisions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.phase1.paraphrase_families.review_human_queue import (  # noqa: E402
    ALLOWED_DECISIONS,
    DEFAULT_QUEUE,
    RESOLVED_COLUMNS,
    ROOT,
    validate_queue,
)
from research.phase1.paraphrase_families.validate_human_review import (  # noqa: E402
    audit_consistency,
    validate_resolved_review,
)


HERE = Path(__file__).resolve().parent
PRIVATE_ROOT = ROOT.parent / f"{ROOT.name}_private" / "phase1"
ORIGINAL_RESOLVED = PRIVATE_ROOT / "human_review_queue_v1_resolved.csv"
CORRECTION_QUEUE = PRIVATE_ROOT / "human_review_correction_queue_v1.csv"
FINAL_PRIVATE_REVIEW = PRIVATE_ROOT / "human_review_queue_v1_final.csv"
COMPONENT_PAIR_REVIEW = PRIVATE_ROOT / "component_review_0001_pairs_v1.csv"
PROVISIONAL_DECISIONS = HERE / "provisional_pair_decisions_v1.csv"
HUMAN_DECISIONS_OUTPUT = HERE / "human_pair_decisions_v1.csv"
FINAL_DECISIONS_OUTPUT = HERE / "final_pair_decisions_v1.csv"
FINAL_CONSISTENCY_OUTPUT = HERE / "human_review_final_consistency_summary_v1.json"

EXPECTED_ORIGINAL_RESOLVED_SHA256 = (
    "902b2942bf3f7f3d62d033d43b03f501015928875c58c9520247700949c232cb"
)
EXPECTED_CORRECTED_PAIR = "NID5-ND-000048"
EXPECTED_ORIGINAL_DECISION = "RELATED_NOT_PARAPHRASE"
EXPECTED_CORRECTED_DECISION = "LABEL_CONFLICT_SAME_MEANING"
EXPECTED_COMPONENT_PAIR_SHA256 = (
    "5f0306c505b00b396a4cae54255280e0d63d2faddb57477184abe2c90f649560"
)
HUMAN_COLUMNS = [
    "review_id",
    "pair_id",
    "sample_id_a",
    "sample_id_b",
    "label_a",
    "label_b",
    "split_a",
    "split_b",
    "human_decision",
    "adjudication_source",
]
FINAL_COLUMNS = [
    "pair_id",
    "sample_id_a",
    "sample_id_b",
    "label_a",
    "label_b",
    "split_a",
    "split_b",
    "char_tfidf_cosine",
    "semantic_decision",
    "semantic_decision_source",
    "family_equivalence",
    "family_equivalence_source",
    "cross_label_equivalence",
    "reason_code",
]
CORRECTION_IMMUTABLE_COLUMNS = [
    "review_id",
    "pair_id",
    "sample_id_a",
    "text_a",
    "label_a",
    "sample_id_b",
    "text_b",
    "label_b",
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


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    columns: list[str],
    *,
    atomic: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path.with_suffix(path.suffix + ".tmp") if atomic else path
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        if atomic:
            handle.flush()
            os.fsync(handle.fileno())
    if atomic:
        target.replace(path)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def validate_correction(
    correction_path: Path,
    original_rows: list[dict[str, str]],
) -> tuple[dict[str, str], str]:
    _, corrections = read_csv(correction_path)
    require(len(corrections) == 1, "HUMAN CORRECTION INVALID: expected one row")
    correction = corrections[0]
    require(
        correction["pair_id"] == EXPECTED_CORRECTED_PAIR,
        "HUMAN CORRECTION INVALID: unexpected pair",
    )
    require(
        correction["corrected_human_decision"] == EXPECTED_CORRECTED_DECISION,
        "HUMAN CORRECTION INVALID: corrected decision is not authorized",
    )
    require(
        correction["current_human_decision"] == EXPECTED_ORIGINAL_DECISION,
        "HUMAN CORRECTION INVALID: original decision differs",
    )
    original_by_pair = {row["pair_id"]: row for row in original_rows}
    original = original_by_pair[EXPECTED_CORRECTED_PAIR]
    for column in CORRECTION_IMMUTABLE_COLUMNS:
        require(
            correction[column] == original[column],
            f"HUMAN CORRECTION INVALID: changed source field {column}",
        )
    return correction, sha256_file(correction_path)


def create_final_private_review(
    original_rows: list[dict[str, str]],
    correction: dict[str, str],
    output_path: Path,
) -> tuple[list[dict[str, str]], str]:
    require(
        not output_path.resolve().is_relative_to(ROOT.resolve()),
        "Final private review must remain outside Git",
    )
    final_rows = [dict(row) for row in original_rows]
    changed = 0
    for row in final_rows:
        if row["pair_id"] == EXPECTED_CORRECTED_PAIR:
            require(
                row["human_decision"] == EXPECTED_ORIGINAL_DECISION,
                "Original human decision unexpectedly changed",
            )
            row["human_decision"] = correction["corrected_human_decision"]
            if correction["human_notes"].strip():
                row["human_notes"] = correction["human_notes"]
            row["reviewer"] = "human"
            changed += 1
    require(changed == 1, "Expected exactly one final human correction")
    write_csv(output_path, final_rows, RESOLVED_COLUMNS, atomic=True)
    return final_rows, sha256_file(output_path)


def create_safe_decisions(
    final_human_rows: list[dict[str, str]],
    provisional_path: Path,
    component_pairs_path: Path,
    human_output: Path,
    final_output: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    human_rows = [
        {
            "review_id": row["review_id"],
            "pair_id": row["pair_id"],
            "sample_id_a": row["sample_id_a"],
            "sample_id_b": row["sample_id_b"],
            "label_a": row["label_a"],
            "label_b": row["label_b"],
            "split_a": row["split_a"],
            "split_b": row["split_b"],
            "human_decision": row["human_decision"],
            "adjudication_source": "human_confirmed",
        }
        for row in final_human_rows
    ]
    require(len(human_rows) == 29, "Expected 29 human decision rows")
    human_by_pair = {row["pair_id"]: row for row in human_rows}
    require(len(human_by_pair) == 29, "Duplicate human pair IDs")
    write_csv(human_output, human_rows, HUMAN_COLUMNS)

    require(
        sha256_file(component_pairs_path) == EXPECTED_COMPONENT_PAIR_SHA256,
        "Component pair review hash mismatch",
    )
    _, component_rows = read_csv(component_pairs_path)
    require(len(component_rows) == 6, "Expected six component pair relations")
    component_by_pair = {row["pair_id"]: row for row in component_rows}
    require(len(component_by_pair) == 6, "Duplicate component pair IDs")

    _, provisional_rows = read_csv(provisional_path)
    require(len(provisional_rows) == 99, "Expected 99 provisional decisions")
    final_rows = []
    for row in provisional_rows:
        human = human_by_pair.get(row["pair_id"])
        if human:
            semantic_decision = human["human_decision"]
            semantic_source = "human_confirmed"
            reason = (
                "HUMAN_CONFIRMED"
                if semantic_decision == row["provisional_decision"]
                else "HUMAN_OVERRIDE"
            )
        else:
            semantic_decision = row["provisional_decision"]
            semantic_source = "codex_provisional"
            require(
                row["confidence"] == "HIGH",
                f"Unreviewed non-high-confidence pair: {row['pair_id']}",
            )
            reason = row["reason_code"]
        require(semantic_decision in ALLOWED_DECISIONS, "Invalid semantic decision")
        require(
            not (
                row["label_a"] != row["label_b"]
                and semantic_decision == "SAME_MEANING"
            ),
            f"Cross-label SAME_MEANING violation: {row['pair_id']}",
        )
        component = component_by_pair.get(row["pair_id"])
        if component:
            family_equivalence = (
                "EQUIVALENT"
                if component["same_human_group"].lower() == "true"
                else "NOT_EQUIVALENT"
            )
            family_source = "human_component_review"
        else:
            family_equivalence = (
                "EQUIVALENT"
                if semantic_decision
                in {"SAME_MEANING", "LABEL_CONFLICT_SAME_MEANING"}
                else "NOT_EQUIVALENT"
            )
            family_source = (
                "human_pair_review"
                if semantic_source == "human_confirmed"
                else "codex_provisional"
            )
        cross_label_equivalence = (
            row["label_a"] != row["label_b"]
            and family_equivalence == "EQUIVALENT"
        )
        if cross_label_equivalence and not component:
            require(
                semantic_decision == "LABEL_CONFLICT_SAME_MEANING",
                f"Cross-label equivalence category mismatch: {row['pair_id']}",
            )
        final_rows.append(
            {
                "pair_id": row["pair_id"],
                "sample_id_a": row["sample_id_a"],
                "sample_id_b": row["sample_id_b"],
                "label_a": row["label_a"],
                "label_b": row["label_b"],
                "split_a": row["split_a"],
                "split_b": row["split_b"],
                "char_tfidf_cosine": row["char_tfidf_cosine"],
                "semantic_decision": semantic_decision,
                "semantic_decision_source": semantic_source,
                "family_equivalence": family_equivalence,
                "family_equivalence_source": family_source,
                "cross_label_equivalence": str(cross_label_equivalence).lower(),
                "reason_code": reason,
            }
        )
    require(len(final_rows) == 99, "Expected 99 final decisions")
    require(
        Counter(row["semantic_decision_source"] for row in final_rows)
        == {"human_confirmed": 29, "codex_provisional": 70},
        "Final semantic provenance counts mismatch",
    )
    require(
        Counter(row["family_equivalence_source"] for row in final_rows)[
            "human_component_review"
        ]
        == 6,
        "Expected six component-level family overrides",
    )
    write_csv(final_output, final_rows, FINAL_COLUMNS)
    return human_rows, final_rows


def finalize(
    source_queue: Path,
    original_resolved: Path,
    correction_queue: Path,
    final_private: Path,
    provisional_decisions: Path,
    component_pairs: Path,
    human_output: Path,
    final_output: Path,
    consistency_output: Path,
) -> dict[str, Any]:
    source_rows = validate_queue(source_queue)
    original_rows = validate_resolved_review(
        source_rows,
        original_resolved,
        EXPECTED_ORIGINAL_RESOLVED_SHA256,
    )
    correction, correction_hash = validate_correction(
        correction_queue,
        original_rows,
    )
    final_rows, final_hash = create_final_private_review(
        original_rows,
        correction,
        final_private,
    )
    validated_final = validate_resolved_review(
        source_rows,
        final_private,
        final_hash,
    )
    consistency, corrections = audit_consistency(validated_final)
    require(
        not corrections,
        "Final human review still contains mandatory contradictions",
    )
    require(
        consistency["ambiguous_remaining"] == 0,
        "Final human review retains ambiguous decisions",
    )
    human_rows, final_decisions = create_safe_decisions(
        validated_final,
        provisional_decisions,
        component_pairs,
        human_output,
        final_output,
    )
    result = {
        **consistency,
        "status": "PASS",
        "original_resolved_sha256": EXPECTED_ORIGINAL_RESOLVED_SHA256,
        "human_correction_queue_sha256": correction_hash,
        "final_private_review_sha256": final_hash,
        "component_pair_review_sha256": sha256_file(component_pairs),
        "human_correction_count": 1,
        "corrected_pair": EXPECTED_CORRECTED_PAIR,
        "human_reviewed_pairs": len(human_rows),
        "codex_only_pairs": sum(
            row["semantic_decision_source"] == "codex_provisional"
            for row in final_decisions
        ),
        "source_text_unchanged": True,
        "source_labels_unchanged": True,
        "original_resolved_modified": False,
    }
    write_json(consistency_output, result)
    require(
        sha256_file(original_resolved) == EXPECTED_ORIGINAL_RESOLVED_SHA256,
        "Original resolved review was modified",
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply the single human-approved correction and freeze safe decisions."
    )
    parser.add_argument("--source-queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--original-resolved", type=Path, default=ORIGINAL_RESOLVED)
    parser.add_argument("--correction-queue", type=Path, default=CORRECTION_QUEUE)
    parser.add_argument("--final-private", type=Path, default=FINAL_PRIVATE_REVIEW)
    parser.add_argument(
        "--provisional-decisions",
        type=Path,
        default=PROVISIONAL_DECISIONS,
    )
    parser.add_argument(
        "--component-pairs",
        type=Path,
        default=COMPONENT_PAIR_REVIEW,
    )
    parser.add_argument("--human-output", type=Path, default=HUMAN_DECISIONS_OUTPUT)
    parser.add_argument("--final-output", type=Path, default=FINAL_DECISIONS_OUTPUT)
    parser.add_argument(
        "--consistency-output",
        type=Path,
        default=FINAL_CONSISTENCY_OUTPUT,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = finalize(
        args.source_queue,
        args.original_resolved,
        args.correction_queue,
        args.final_private,
        args.provisional_decisions,
        args.component_pairs,
        args.human_output,
        args.final_output,
        args.consistency_output,
    )
    print("FINAL HUMAN REVIEW CONSISTENCY:", result["status"])
    print("HUMAN REVIEWED PAIRS:", result["human_reviewed_pairs"])
    print("MACHINE-ASSISTED PAIRS:", result["codex_only_pairs"])
    print("FINAL PRIVATE SHA-256:", result["final_private_review_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
