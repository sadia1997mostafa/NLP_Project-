"""Interactively review the private NID5-SHIFT-V1 seed candidate queue."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path


BASE_FIELDS = (
    "review_index", "sample_id", "text", "source_label_id", "source_label_name",
    "canonical_label_id", "canonical_label_name", "phase0_split",
    "paraphrase_family_id", "script_profile", "length_band", "classifiable",
    "explicit_enough", "transformable", "review_decision", "human_notes",
)
RESOLVED_FIELDS = BASE_FIELDS + ("reviewer", "review_timestamp")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_resolved(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RESOLVED_FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def derive_decision(classifiable: str, explicit_enough: str, transformable: str) -> str:
    values = (classifiable.upper(), explicit_enough.upper(), transformable.upper())
    if any(value not in {"YES", "NO"} for value in values):
        raise ValueError("All semantic checks must be YES or NO")
    return "ACCEPT" if values == ("YES", "YES", "YES") else "REJECT"


def load_review_state(queue_path: Path, resolved_path: Path) -> list[dict[str, str]]:
    queue_rows = read_csv(queue_path)
    if len(queue_rows) != 100:
        raise ValueError(f"Expected 100 queue rows, found {len(queue_rows)}")
    if tuple(queue_rows[0]) != BASE_FIELDS:
        raise ValueError("Private review queue schema mismatch")
    if not resolved_path.exists():
        return [{**row, "reviewer": "", "review_timestamp": ""} for row in queue_rows]

    resolved_rows = read_csv(resolved_path)
    if len(resolved_rows) != len(queue_rows):
        raise ValueError("Resolved review row count differs from queue")
    if tuple(resolved_rows[0]) != RESOLVED_FIELDS:
        raise ValueError("Resolved review schema mismatch")
    immutable = BASE_FIELDS[:11]
    for queue_row, resolved_row in zip(queue_rows, resolved_rows, strict=True):
        for field in immutable:
            if queue_row[field] != resolved_row[field]:
                raise ValueError(f"Resolved review changed immutable field {field}")
        decision = resolved_row["review_decision"]
        if decision:
            expected = derive_decision(
                resolved_row["classifiable"],
                resolved_row["explicit_enough"],
                resolved_row["transformable"],
            )
            if decision != expected or resolved_row["reviewer"] != "human":
                raise ValueError("Invalid completed human review row")
    return resolved_rows


def _ask_yes_no(prompt: str) -> str:
    while True:
        value = input(prompt).strip().upper()
        if value == "S":
            return "S"
        if value in {"Y", "YES"}:
            return "YES"
        if value in {"N", "NO"}:
            return "NO"
        print("Enter Y, N, or S to save and exit.")


def main() -> None:
    root = repository_root()
    private_dir = root.parent / f"{root.name}_private" / "phase1"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=private_dir / "challenge_seed_review_queue_v1.csv")
    parser.add_argument("--resolved", type=Path, default=private_dir / "challenge_seed_review_v1_resolved.csv")
    args = parser.parse_args()
    rows = load_review_state(args.queue, args.resolved)

    completed = sum(bool(row["review_decision"]) for row in rows)
    print(f"Completed: {completed} / 100")
    print(f"Remaining: {100 - completed} / 100")
    for row in rows:
        if row["review_decision"]:
            continue
        print("\n" + "=" * 60)
        print(f"SEED REVIEW {row['review_index']} / 100")
        print(f"\nSample ID:\n{row['sample_id']}")
        print(f"\nFrozen label:\n{row['source_label_name']}")
        print(f"\nCanonical label:\n{row['canonical_label_name']}")
        print(f"\nFamily:\n{row['paraphrase_family_id']}")
        print(f"\nScript profile:\n{row['script_profile']}")
        print(f"\nLength band:\n{row['length_band']}")
        print(f"\nText:\n{row['text']}")
        print("\nEnter S at a Y/N prompt to save and exit.")
        classifiable = _ask_yes_no("\n1. Classifiable under FROZEN_V1? [Y/N/S]: ")
        if classifiable == "S":
            write_resolved(args.resolved, rows)
            return
        explicit = _ask_yes_no("2. Explicit enough to preserve the information need? [Y/N/S]: ")
        if explicit == "S":
            write_resolved(args.resolved, rows)
            return
        transformable = _ask_yes_no("3. Suitable for C1-C4 meaning-preserving transformations? [Y/N/S]: ")
        if transformable == "S":
            write_resolved(args.resolved, rows)
            return
        decision = derive_decision(classifiable, explicit, transformable)
        notes = input("Optional human notes: ").strip()
        print(f"\nDerived review decision: {decision}")
        confirmation = _ask_yes_no("Confirm? [Y/N/S]: ")
        if confirmation == "S":
            write_resolved(args.resolved, rows)
            return
        if confirmation == "NO":
            print("Decision not saved; presenting this seed again.")
            return main()
        row.update(
            {
                "classifiable": classifiable,
                "explicit_enough": explicit,
                "transformable": transformable,
                "review_decision": decision,
                "human_notes": notes,
                "reviewer": "human",
                "review_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        write_resolved(args.resolved, rows)
        completed += 1
        print(f"Completed: {completed} / 100")
        print(f"Remaining: {100 - completed} / 100")

    print("HUMAN SEED REVIEW COMPLETE: 100 / 100")


if __name__ == "__main__":
    main()
