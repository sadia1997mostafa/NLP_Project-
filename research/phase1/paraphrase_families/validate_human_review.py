"""Validate completed human paraphrase review without changing decisions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.phase1.paraphrase_families.review_human_queue import (
    ALLOWED_DECISIONS,
    DEFAULT_QUEUE,
    RESOLVED_COLUMNS,
    ROOT,
    SOURCE_COLUMNS,
    validate_private_output_path,
    validate_queue,
)


HERE = Path(__file__).resolve().parent
PRIVATE_ROOT = ROOT.parent / f"{ROOT.name}_private" / "phase1"
DEFAULT_RESOLVED = PRIVATE_ROOT / "human_review_queue_v1_resolved.csv"
DEFAULT_CORRECTION_QUEUE = PRIVATE_ROOT / "human_review_correction_queue_v1.csv"
DEFAULT_SUMMARY = HERE / "human_review_consistency_summary_v1.json"
EXPECTED_RESOLVED_SHA256 = (
    "902b2942bf3f7f3d62d033d43b03f501015928875c58c9520247700949c232cb"
)
EXPECTED_PHASE0_MANIFEST_SHA256 = (
    "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
)
EQUIVALENT = {"SAME_MEANING", "LABEL_CONFLICT_SAME_MEANING"}
IMMUTABLE_COLUMNS = SOURCE_COLUMNS[:-2]
CORRECTION_COLUMNS = [
    "correction_id",
    "review_id",
    "pair_id",
    "sample_id_a",
    "text_a",
    "label_a",
    "sample_id_b",
    "text_b",
    "label_b",
    "current_human_decision",
    "violation_type",
    "suggested_valid_decision",
    "corrected_human_decision",
    "human_notes",
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


def normalize_text(value: object) -> str:
    """Frozen minimal equality normalization: NFC plus whitespace collapse."""
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def validate_resolved_review(
    source_rows: list[dict[str, str]],
    resolved_path: Path,
    expected_sha256: str = EXPECTED_RESOLVED_SHA256,
) -> list[dict[str, str]]:
    validate_private_output_path(resolved_path)
    require(resolved_path.exists(), f"Resolved review file not found: {resolved_path}")
    require(
        sha256_file(resolved_path) == expected_sha256,
        "RESOLVED HUMAN REVIEW ARTIFACT MISMATCH",
    )
    fields, rows = read_csv(resolved_path)
    require(fields == RESOLVED_COLUMNS, "Resolved review schema mismatch")
    require(len(rows) == 29, "Expected 29 resolved review rows")
    require(len({row["review_id"] for row in rows}) == 29, "Duplicate review IDs")
    require(len({row["pair_id"] for row in rows}) == 29, "Duplicate pair IDs")
    require(all(row["human_decision"] for row in rows), "Missing human decisions")
    require(
        {row["human_decision"] for row in rows}.issubset(ALLOWED_DECISIONS),
        "Invalid human decision vocabulary",
    )

    source_by_review = {row["review_id"]: row for row in source_rows}
    require(
        set(source_by_review) == {row["review_id"] for row in rows},
        "Resolved review IDs differ from frozen queue",
    )
    for row in rows:
        source = source_by_review[row["review_id"]]
        for column in IMMUTABLE_COLUMNS:
            require(
                row[column] == source[column],
                f"Frozen source field changed for {row['review_id']}: {column}",
            )
        require(row["reviewer"] == "human", "Completed reviewer must be human")
        require(bool(row["review_timestamp"]), "Completed decision lacks timestamp")
    return rows


def audit_consistency(
    rows: list[dict[str, str]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    exact_same_label = 0
    exact_cross_label = 0
    cross_label_equivalence = 0
    ambiguous_remaining = 0
    correction_rows: list[dict[str, str]] = []

    for row in rows:
        exact = normalize_text(row["text_a"]) == normalize_text(row["text_b"])
        same_label = row["label_a"] == row["label_b"]
        decision = row["human_decision"]
        if exact and same_label:
            exact_same_label += 1
        if exact and not same_label:
            exact_cross_label += 1
        if not same_label and decision in EQUIVALENT:
            cross_label_equivalence += 1
        if decision == "AMBIGUOUS_REVIEW_REQUIRED":
            ambiguous_remaining += 1

        violation = None
        suggestion = None
        if exact and same_label and decision != "SAME_MEANING":
            violation = "EXACT_TEXT_SEMANTIC_CONTRADICTION"
            suggestion = "SAME_MEANING"
        elif exact and not same_label and decision != "LABEL_CONFLICT_SAME_MEANING":
            violation = "EXACT_TEXT_LABEL_CONFLICT_CONTRADICTION"
            suggestion = "LABEL_CONFLICT_SAME_MEANING"
        elif not same_label and decision == "SAME_MEANING":
            violation = "CROSS_LABEL_EQUIVALENCE_ENCODING_CONTRADICTION"
            suggestion = "LABEL_CONFLICT_SAME_MEANING"

        if violation:
            correction_rows.append(
                {
                    "correction_id": f"NID5-HC-V1-{len(correction_rows) + 1:04d}",
                    "review_id": row["review_id"],
                    "pair_id": row["pair_id"],
                    "sample_id_a": row["sample_id_a"],
                    "text_a": row["text_a"],
                    "label_a": row["label_a"],
                    "sample_id_b": row["sample_id_b"],
                    "text_b": row["text_b"],
                    "label_b": row["label_b"],
                    "current_human_decision": decision,
                    "violation_type": violation,
                    "suggested_valid_decision": suggestion,
                    "corrected_human_decision": "",
                    "human_notes": "",
                }
            )

    summary = {
        "reviewed_pairs": len(rows),
        "exact_same_label_pairs": exact_same_label,
        "exact_cross_label_pairs": exact_cross_label,
        "cross_label_equivalence_pairs": cross_label_equivalence,
        "ambiguous_remaining": ambiguous_remaining,
        "mandatory_rereview_count": len(correction_rows),
        "warning_count": ambiguous_remaining,
        "mandatory_pair_ids": [row["pair_id"] for row in correction_rows],
        "status": (
            "REQUIRES_HUMAN_CORRECTION" if correction_rows else "PASS"
        ),
    }
    return summary, correction_rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_correction_queue(path: Path, rows: list[dict[str, str]]) -> None:
    validate_private_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CORRECTION_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def validate_and_write(
    source_queue: Path,
    resolved_path: Path,
    summary_path: Path,
    correction_queue: Path | None,
    expected_resolved_sha256: str = EXPECTED_RESOLVED_SHA256,
) -> dict[str, Any]:
    before_hash = sha256_file(resolved_path)
    source_rows = validate_queue(source_queue)
    rows = validate_resolved_review(
        source_rows,
        resolved_path,
        expected_sha256=expected_resolved_sha256,
    )
    summary, corrections = audit_consistency(rows)
    summary.update(
        {
            "resolved_review_sha256": before_hash,
            "all_decisions_present": True,
            "decision_vocabulary_valid": True,
            "source_text_unchanged": True,
            "source_labels_unchanged": True,
            "resolved_file_modified": False,
            "phase0_manifest_sha256": EXPECTED_PHASE0_MANIFEST_SHA256,
        }
    )
    if corrections and correction_queue is not None:
        write_correction_queue(correction_queue, corrections)
        summary["private_correction_queue"] = {
            "path": str(correction_queue.resolve()),
            "rows": len(corrections),
            "sha256": sha256_file(correction_queue),
        }
    else:
        summary["private_correction_queue"] = None
    write_json(summary_path, summary)
    require(
        sha256_file(resolved_path) == before_hash,
        "Validator modified the resolved human review",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate completed human paraphrase review and identify only "
            "hard logical contradictions."
        )
    )
    parser.add_argument("--source-queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--resolved", type=Path, default=DEFAULT_RESOLVED)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--correction-queue",
        type=Path,
        default=DEFAULT_CORRECTION_QUEUE,
    )
    parser.add_argument(
        "--no-correction-queue",
        action="store_true",
        help="Validate and write the Git-safe summary without a private queue.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    correction_queue = None if args.no_correction_queue else args.correction_queue
    summary = validate_and_write(
        args.source_queue,
        args.resolved,
        args.summary,
        correction_queue,
    )
    print("HUMAN REVIEW CONSISTENCY:", summary["status"])
    print("REVIEWED PAIRS:", summary["reviewed_pairs"])
    print("MANDATORY RE-REVIEW:", summary["mandatory_rereview_count"])
    print("REMAINING AMBIGUOUS:", summary["ambiguous_remaining"])
    if summary["mandatory_pair_ids"]:
        print("PAIR IDS:", ", ".join(summary["mandatory_pair_ids"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
