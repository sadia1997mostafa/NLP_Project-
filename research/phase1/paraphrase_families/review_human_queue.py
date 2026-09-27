"""Interactive, resumable human review for the private paraphrase queue.

This program records reviewer choices. It never infers or fills a human
decision itself, and it never writes raw query text inside the Git repository.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PRIVATE_ROOT = ROOT.parent / f"{ROOT.name}_private" / "phase1"
DEFAULT_QUEUE = PRIVATE_ROOT / "human_review_queue_v1.csv"
DEFAULT_RESOLVED = PRIVATE_ROOT / "human_review_queue_v1_resolved.csv"
EXPECTED_QUEUE_SHA256 = (
    "1e373fde76200a73d0d25371e8a6e1ddf449ba34be72afa3477e37b0424a0520"
)
EXPECTED_ROWS = 29

DECISION_CHOICES = {
    "1": "SAME_MEANING",
    "2": "SAME_TEMPLATE_DIFFERENT_MEANING",
    "3": "RELATED_NOT_PARAPHRASE",
    "4": "LABEL_CONFLICT_SAME_MEANING",
    "5": "AMBIGUOUS_REVIEW_REQUIRED",
    "6": "NOT_PARAPHRASE",
}
ALLOWED_DECISIONS = set(DECISION_CHOICES.values())
SOURCE_COLUMNS = [
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
RESOLVED_COLUMNS = SOURCE_COLUMNS + ["reviewer", "review_timestamp"]


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


def validate_queue(path: Path) -> list[dict[str, str]]:
    require(path.exists(), f"Private review queue not found: {path}")
    require(
        sha256_file(path) == EXPECTED_QUEUE_SHA256,
        "PRIVATE REVIEW ARTIFACT MISMATCH",
    )
    fields, rows = read_csv(path)
    require(fields == SOURCE_COLUMNS, "Private review queue schema mismatch")
    require(len(rows) == EXPECTED_ROWS, f"Expected {EXPECTED_ROWS} queue rows")
    require(
        len({row["review_id"] for row in rows}) == EXPECTED_ROWS,
        "Duplicate review IDs in private queue",
    )
    require(
        len({row["pair_id"] for row in rows}) == EXPECTED_ROWS,
        "Duplicate pair IDs in private queue",
    )
    require(
        all(not row["human_decision"] and not row["human_notes"] for row in rows),
        "Source review queue unexpectedly contains human decisions",
    )
    return rows


def validate_private_output_path(path: Path) -> None:
    require(
        not path.resolve().is_relative_to(ROOT.resolve()),
        "Resolved review file must remain outside the Git repository",
    )


def load_progress(
    queue_rows: list[dict[str, str]], resolved_path: Path
) -> list[dict[str, str]]:
    if not resolved_path.exists():
        return [
            {
                **{column: row[column] for column in SOURCE_COLUMNS},
                "reviewer": "",
                "review_timestamp": "",
            }
            for row in queue_rows
        ]

    fields, resolved_rows = read_csv(resolved_path)
    require(fields == RESOLVED_COLUMNS, "Resolved review schema mismatch")
    require(len(resolved_rows) == EXPECTED_ROWS, "Resolved review row count mismatch")
    require(
        len({row["review_id"] for row in resolved_rows}) == EXPECTED_ROWS,
        "Duplicate review IDs in resolved review file",
    )
    require(
        len({row["pair_id"] for row in resolved_rows}) == EXPECTED_ROWS,
        "Duplicate pair IDs in resolved review file",
    )

    queue_by_id = {row["review_id"]: row for row in queue_rows}
    require(
        set(queue_by_id) == {row["review_id"] for row in resolved_rows},
        "Resolved review IDs differ from the frozen queue",
    )
    for row in resolved_rows:
        source = queue_by_id[row["review_id"]]
        for column in SOURCE_COLUMNS[:-2]:
            require(
                row[column] == source[column],
                f"Frozen queue content changed for {row['review_id']}: {column}",
            )
        decision = row["human_decision"]
        require(
            not decision or decision in ALLOWED_DECISIONS,
            f"Invalid human decision for {row['review_id']}",
        )
        if decision:
            require(row["reviewer"] == "human", "Completed decision reviewer must be human")
            require(bool(row["review_timestamp"]), "Completed decision needs a timestamp")
            require(
                not (
                    row["label_a"] != row["label_b"]
                    and decision == "SAME_MEANING"
                ),
                "Cross-label SAME_MEANING is forbidden; use LABEL_CONFLICT_SAME_MEANING",
            )
        else:
            require(
                not row["reviewer"] and not row["review_timestamp"],
                "Incomplete decision cannot have reviewer metadata",
            )
    return resolved_rows


def save_progress(path: Path, rows: list[dict[str, str]]) -> None:
    validate_private_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=RESOLVED_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def progress_counts(rows: list[dict[str, str]]) -> tuple[int, int]:
    completed = sum(bool(row["human_decision"]) for row in rows)
    return completed, len(rows) - completed


def display_case(row: dict[str, str], position: int, total: int) -> None:
    print("\n" + "-" * 72)
    print(f"Review {position} / {total}")
    print(f"\nPair ID:\n{row['pair_id']}")
    print("\nSample A:")
    print(f"Text:\n{row['text_a']}")
    print(f"Source label:\n{row['label_a']}")
    print(f"Phase 0 split:\n{row['split_a']}")
    print("\nSample B:")
    print(f"Text:\n{row['text_b']}")
    print(f"Source label:\n{row['label_b']}")
    print(f"Phase 0 split:\n{row['split_b']}")
    print(f"\nSimilarity:\n{row['similarity']}")
    print(f"\nCodex provisional decision:\n{row['codex_provisional_decision']}")
    print(f"\nCodex confidence:\n{row['codex_confidence']}")
    print(f"\nCodex reason:\n{row['codex_reason_code']}")
    print(
        "\nPlease choose:\n"
        "1 = SAME_MEANING\n"
        "2 = SAME_TEMPLATE_DIFFERENT_MEANING\n"
        "3 = RELATED_NOT_PARAPHRASE\n"
        "4 = LABEL_CONFLICT_SAME_MEANING\n"
        "5 = AMBIGUOUS_REVIEW_REQUIRED\n"
        "6 = NOT_PARAPHRASE\n"
        "S = skip/save/exit"
    )
    print("-" * 72)


def prompt_for_decision(row: dict[str, str]) -> str | None:
    while True:
        choice = input("Decision [1-6/S]: ").strip().upper()
        if choice == "S":
            return None
        if choice not in DECISION_CHOICES:
            print("Invalid choice. Enter 1-6 or S.")
            continue
        decision = DECISION_CHOICES[choice]
        if row["label_a"] != row["label_b"] and decision == "SAME_MEANING":
            print(
                "Cross-label equivalent queries must be saved as "
                "LABEL_CONFLICT_SAME_MEANING. Choose 4, or another decision."
            )
            continue
        return decision


def run_review(queue_path: Path, resolved_path: Path, status_only: bool = False) -> int:
    validate_private_output_path(resolved_path)
    queue_rows = validate_queue(queue_path)
    rows = load_progress(queue_rows, resolved_path)
    completed, remaining = progress_counts(rows)
    print(f"Completed: {completed} / {len(rows)}")
    print(f"Remaining: {remaining} / {len(rows)}")

    if status_only or remaining == 0:
        if remaining == 0:
            print("HUMAN REVIEW COMPLETE")
            print(f"Resolved SHA-256: {sha256_file(resolved_path)}")
        return 0

    for position, row in enumerate(rows, start=1):
        if row["human_decision"]:
            continue
        display_case(row, position, len(rows))
        decision = prompt_for_decision(row)
        if decision is None:
            save_progress(resolved_path, rows)
            completed, remaining = progress_counts(rows)
            print(f"\nCompleted: {completed} / {len(rows)}")
            print(f"Remaining: {remaining} / {len(rows)}")
            print("HUMAN REVIEW INCOMPLETE")
            return 0
        notes = input("Optional human notes (press Enter to leave blank): ").strip()
        row["human_decision"] = decision
        row["human_notes"] = notes
        row["reviewer"] = "human"
        row["review_timestamp"] = datetime.now(timezone.utc).isoformat()
        save_progress(resolved_path, rows)
        completed, remaining = progress_counts(rows)
        print(f"Saved. Completed: {completed} / {len(rows)}; Remaining: {remaining}")

    print("\nHUMAN REVIEW COMPLETE")
    print(f"Resolved SHA-256: {sha256_file(resolved_path)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Interactively record human decisions for the private Phase 1 "
            "paraphrase-family review queue."
        )
    )
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--resolved", type=Path, default=DEFAULT_RESOLVED)
    parser.add_argument(
        "--status",
        action="store_true",
        help="Validate files and report progress without prompting or writing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_review(args.queue, args.resolved, status_only=args.status)


if __name__ == "__main__":
    raise SystemExit(main())
