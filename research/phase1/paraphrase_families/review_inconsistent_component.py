"""Interactive human grouping for the single inconsistent four-sample component."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIVATE_ROOT = ROOT.parent / f"{ROOT.name}_private" / "phase1"
DEFAULT_RAW_PAIRS = PRIVATE_ROOT / "near_duplicate_review_v1.csv"
DEFAULT_DECISIONS = HERE / "final_pair_decisions_v1.csv"
DEFAULT_COMPONENT_OUTPUT = PRIVATE_ROOT / "component_review_0001_v1.csv"
DEFAULT_PAIR_OUTPUT = PRIVATE_ROOT / "component_review_0001_pairs_v1.csv"

REQUIRED_SAMPLE_IDS = (
    "NID5-V1-000769",
    "NID5-V1-000826",
    "NID5-V1-000894",
    "NID5-V1-001449",
)
REQUIRED_PAIR_IDS = (
    "NID5-ND-000056",
    "NID5-ND-000057",
    "NID5-ND-000058",
    "NID5-ND-000067",
    "NID5-ND-000068",
    "NID5-ND-000071",
)
EQUIVALENT = {"SAME_MEANING", "LABEL_CONFLICT_SAME_MEANING"}
HUMAN_COMPONENT_COLUMNS = [
    "sample_id",
    "text",
    "source_label",
    "phase0_split",
    "human_semantic_group",
    "reviewer",
    "review_timestamp",
]
PAIR_DERIVATION_COLUMNS = [
    "pair_id",
    "sample_id_a",
    "sample_id_b",
    "same_human_group",
    "derived_equivalence_decision",
    "existing_decision",
    "existing_source",
    "needs_non_equivalence_category_change",
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


def validate_private_path(path: Path) -> None:
    require(
        not path.resolve().is_relative_to(ROOT.resolve()),
        "Component review outputs must remain outside Git",
    )


def load_component(
    raw_pairs_path: Path,
    decisions_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    validate_private_path(raw_pairs_path)
    raw_rows = [
        row
        for row in read_csv(raw_pairs_path)
        if row["pair_id"] in REQUIRED_PAIR_IDS
    ]
    decision_rows = [
        row
        for row in read_csv(decisions_path)
        if row["pair_id"] in REQUIRED_PAIR_IDS
    ]
    require(len(raw_rows) == 6, "Expected six private component relations")
    require(len(decision_rows) == 6, "Expected six current component decisions")
    require(
        {row["pair_id"] for row in raw_rows} == set(REQUIRED_PAIR_IDS),
        "Private component pair IDs mismatch",
    )
    require(
        {row["pair_id"] for row in decision_rows} == set(REQUIRED_PAIR_IDS),
        "Decision component pair IDs mismatch",
    )

    samples: dict[str, dict[str, str]] = {}
    raw_by_pair = {row["pair_id"]: row for row in raw_rows}
    for row in raw_rows:
        for suffix in ("a", "b"):
            sample_id = row[f"sample_id_{suffix}"]
            value = {
                "sample_id": sample_id,
                "text": row[f"text_{suffix}"],
                "source_label": row[f"label_{suffix}"],
                "phase0_split": row[f"split_{suffix}"],
            }
            if sample_id in samples:
                require(samples[sample_id] == value, f"Inconsistent raw sample {sample_id}")
            samples[sample_id] = value
    require(set(samples) == set(REQUIRED_SAMPLE_IDS), "Component sample IDs mismatch")

    decision_by_pair = {row["pair_id"]: row for row in decision_rows}
    complete_pairs = {
        frozenset(pair) for pair in itertools.combinations(REQUIRED_SAMPLE_IDS, 2)
    }
    observed_pairs = {
        frozenset((row["sample_id_a"], row["sample_id_b"]))
        for row in decision_rows
    }
    require(observed_pairs == complete_pairs, "Component is not a complete six-pair graph")
    for pair_id, decision in decision_by_pair.items():
        raw = raw_by_pair[pair_id]
        require(
            decision["sample_id_a"] == raw["sample_id_a"]
            and decision["sample_id_b"] == raw["sample_id_b"],
            f"Pair endpoint mismatch: {pair_id}",
        )
        require(
            decision["label_a"] == raw["label_a"]
            and decision["label_b"] == raw["label_b"],
            f"Pair label mismatch: {pair_id}",
        )
    ordered_samples = [samples[sample_id] for sample_id in REQUIRED_SAMPLE_IDS]
    ordered_pairs = sorted(decision_rows, key=lambda row: row["pair_id"])
    return ordered_samples, ordered_pairs


def normalize_groups(assignments: dict[str, str]) -> dict[str, str]:
    require(set(assignments) == set(REQUIRED_SAMPLE_IDS), "Grouping sample IDs mismatch")
    mapping: dict[str, str] = {}
    normalized: dict[str, str] = {}
    next_index = 0
    canonical = ("A", "B", "C", "D")
    for sample_id in REQUIRED_SAMPLE_IDS:
        raw_group = assignments[sample_id].strip().upper()
        require(raw_group in canonical, f"Invalid group for {sample_id}")
        if raw_group not in mapping:
            mapping[raw_group] = canonical[next_index]
            next_index += 1
        normalized[sample_id] = mapping[raw_group]
    return normalized


def derive_pair_relations(
    samples: list[dict[str, str]],
    pairs: list[dict[str, str]],
    groups: dict[str, str],
) -> list[dict[str, str]]:
    sample_by_id = {row["sample_id"]: row for row in samples}
    derived = []
    for row in pairs:
        left, right = row["sample_id_a"], row["sample_id_b"]
        same_group = groups[left] == groups[right]
        existing = row.get("semantic_decision") or row.get("final_decision", "")
        source = row.get("semantic_decision_source") or row.get(
            "decision_source", ""
        )
        require(bool(existing) and bool(source), "Missing existing decision provenance")
        needs_non_equivalence_change = False
        if same_group:
            decision = (
                "SAME_MEANING"
                if sample_by_id[left]["source_label"]
                == sample_by_id[right]["source_label"]
                else "LABEL_CONFLICT_SAME_MEANING"
            )
        elif source == "human_confirmed" and existing not in EQUIVALENT:
            decision = existing
        else:
            decision = "COMPONENT_REVIEW_NOT_EQUIVALENT"
            needs_non_equivalence_change = True
        derived.append(
            {
                "pair_id": row["pair_id"],
                "sample_id_a": left,
                "sample_id_b": right,
                "same_human_group": str(same_group).lower(),
                "derived_equivalence_decision": decision,
                "existing_decision": existing,
                "existing_source": source,
                "needs_non_equivalence_category_change": str(
                    needs_non_equivalence_change
                ).lower(),
            }
        )
    return derived


def grouping_is_consistent(
    groups: dict[str, str],
    derived_pairs: list[dict[str, str]],
) -> bool:
    by_pair = {
        frozenset((row["sample_id_a"], row["sample_id_b"])): row
        for row in derived_pairs
    }
    for left, right in itertools.combinations(REQUIRED_SAMPLE_IDS, 2):
        row = by_pair[frozenset((left, right))]
        represented_equivalent = row["derived_equivalence_decision"] in EQUIVALENT
        if represented_equivalent != (groups[left] == groups[right]):
            return False
    return True


def display_component(
    samples: list[dict[str, str]],
    pairs: list[dict[str, str]],
) -> None:
    print("=" * 72)
    print("INCONSISTENT COMPONENT REVIEW")
    for number, sample in enumerate(samples, start=1):
        print(f"\nSample {number}")
        print(f"ID: {sample['sample_id']}")
        print(f"Label: {sample['source_label']}")
        print(f"Split: {sample['phase0_split']}")
        print(f"Text: {sample['text']}")
    print("\n" + "=" * 72)
    print("Existing pair decisions (context only):")
    for row in pairs:
        existing = row.get("semantic_decision") or row.get("final_decision", "")
        source = row.get("semantic_decision_source") or row.get(
            "decision_source", ""
        )
        print(
            f"{row['pair_id']}: {row['sample_id_a']} <-> "
            f"{row['sample_id_b']} = {existing} "
            f"({source})"
        )
    print("\nDo not decide pair-by-pair. Assign samples to semantic groups.")
    print("Same group = same meaning; different groups = not equivalent.")
    print("=" * 72)


def prompt_groups() -> dict[str, str]:
    assignments = {}
    for sample_id in REQUIRED_SAMPLE_IDS:
        while True:
            value = input(f"Sample {sample_id} group [A/B/C/D]: ").strip().upper()
            if value in {"A", "B", "C", "D"}:
                assignments[sample_id] = value
                break
            print("Invalid group. Enter A, B, C, or D.")
    return normalize_groups(assignments)


def print_confirmation(
    groups: dict[str, str],
    derived_pairs: list[dict[str, str]],
) -> None:
    print("\nSemantic groups:")
    for group in sorted(set(groups.values())):
        members = [sample_id for sample_id in REQUIRED_SAMPLE_IDS if groups[sample_id] == group]
        print(f"Group {group}: {members}")
    equivalent = [
        row["pair_id"]
        for row in derived_pairs
        if row["derived_equivalence_decision"] in EQUIVALENT
    ]
    non_equivalent = [
        row["pair_id"]
        for row in derived_pairs
        if row["derived_equivalence_decision"] not in EQUIVALENT
    ]
    cross_label = [
        row["pair_id"]
        for row in derived_pairs
        if row["derived_equivalence_decision"] == "LABEL_CONFLICT_SAME_MEANING"
    ]
    print(f"\nDerived equivalent pairs: {equivalent}")
    print(f"Derived non-equivalent pairs: {non_equivalent}")
    print(f"Cross-label equivalent pairs: {cross_label}")


def write_csv_atomic(
    path: Path,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> None:
    validate_private_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def save_confirmed_review(
    samples: list[dict[str, str]],
    groups: dict[str, str],
    derived_pairs: list[dict[str, str]],
    component_output: Path,
    pair_output: Path,
) -> tuple[str, str]:
    require(
        grouping_is_consistent(groups, derived_pairs),
        "Component grouping is not transitively consistent",
    )
    require(not component_output.exists(), f"Refusing to overwrite {component_output}")
    require(not pair_output.exists(), f"Refusing to overwrite {pair_output}")
    timestamp = datetime.now(timezone.utc).isoformat()
    component_rows = [
        {
            **sample,
            "human_semantic_group": groups[sample["sample_id"]],
            "reviewer": "human",
            "review_timestamp": timestamp,
        }
        for sample in samples
    ]
    write_csv_atomic(component_output, component_rows, HUMAN_COMPONENT_COLUMNS)
    write_csv_atomic(pair_output, derived_pairs, PAIR_DERIVATION_COLUMNS)
    return sha256_file(component_output), sha256_file(pair_output)


def run_review(
    raw_pairs: Path,
    decisions: Path,
    component_output: Path,
    pair_output: Path,
    *,
    status_only: bool = False,
) -> int:
    validate_private_path(component_output)
    validate_private_path(pair_output)
    samples, pairs = load_component(raw_pairs, decisions)
    if status_only:
        print(f"Samples loaded: {len(samples)} / 4")
        print(f"Relations loaded: {len(pairs)} / 6")
        print("Human component grouping completed:", component_output.exists())
        return 0
    require(
        not component_output.exists() and not pair_output.exists(),
        "A component review output already exists; refusing to overwrite it",
    )
    display_component(samples, pairs)
    groups = prompt_groups()
    derived_pairs = derive_pair_relations(samples, pairs, groups)
    require(
        grouping_is_consistent(groups, derived_pairs),
        "Component grouping failed transitive consistency",
    )
    print_confirmation(groups, derived_pairs)
    confirm = input("\nConfirm this grouping? [Y/N]: ").strip().upper()
    if confirm != "Y":
        print("Grouping not saved.")
        return 0
    component_hash, pair_hash = save_confirmed_review(
        samples,
        groups,
        derived_pairs,
        component_output,
        pair_output,
    )
    print("\nCOMPONENT REVIEW COMPLETE")
    print("Equivalence graph consistency: PASS")
    print("Component review SHA-256:", component_hash)
    print("Pair derivation SHA-256:", pair_hash)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect a human semantic grouping for the inconsistent "
            "four-sample component."
        )
    )
    parser.add_argument("--raw-pairs", type=Path, default=DEFAULT_RAW_PAIRS)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument(
        "--component-output",
        type=Path,
        default=DEFAULT_COMPONENT_OUTPUT,
    )
    parser.add_argument("--pair-output", type=Path, default=DEFAULT_PAIR_OUTPUT)
    parser.add_argument(
        "--status",
        action="store_true",
        help="Validate inputs and report counts without displaying raw text.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_review(
        args.raw_pairs,
        args.decisions,
        args.component_output,
        args.pair_output,
        status_only=args.status,
    )


if __name__ == "__main__":
    raise SystemExit(main())
