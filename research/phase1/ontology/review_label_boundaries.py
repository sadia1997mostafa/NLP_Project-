"""Interactively adjudicate three frozen five-class boundary conflicts.

This tool never decides a boundary automatically. Raw text is read from and
written to the external private research directory only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Iterable

import yaml


EXPECTED_QUEUE_SHA256 = "11d88b5dc0a5450f252ea5d46f6bb9a893cd8d054e9e715d8b6e01393a6dfda0"
EXPECTED_FAMILY_MAP_SHA256 = "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c"
EXPECTED_PAIR_IDS = ("NID5-ND-000048", "NID5-ND-000050", "NID5-ND-000071")
LABEL_IDS = {
    "NID Information Correction": 0,
    "New NID Registration": 1,
    "Lost/Stolen NID": 2,
    "NID Online Problem": 3,
    "Smart ID Card": 4,
}
DECISIONS = {
    "1": "CANONICAL_LABEL_A",
    "2": "CANONICAL_LABEL_B",
    "3": "CLARIFY_REQUIRED",
    "4": "EXCLUDE_FROM_STRICT_BOUNDARY_EVIDENCE",
}
ALLOWED_DECISIONS = set(DECISIONS.values())
OUTPUT_FIELDS = (
    "boundary_review_id",
    "pair_id",
    "sample_id_a",
    "text_a",
    "source_label_a",
    "sample_id_b",
    "text_b",
    "source_label_b",
    "canonical_boundary_decision",
    "canonical_label_id",
    "canonical_label_name",
    "human_notes",
    "reviewer",
    "review_timestamp",
)
GUIDANCE = (
    "1. Decide according to the requested citizen action / information need.\n"
    "2. Prefer the most specific service lifecycle represented by the current five labels.\n"
    "3. Mentioning 'Smart NID' alone does NOT automatically force Smart ID Card.\n"
    "4. For replacement/reissue after loss or damage, compare carefully with Lost/Stolen NID.\n"
    "5. For routine Smart issuance/readiness/distribution/collection, compare carefully with Smart ID Card.\n"
    "6. Use CLARIFY_REQUIRED only when the query truly lacks enough context.\n"
    "7. Historical label disagreement alone is not semantic ambiguity.\n"
    "8. Do not change either source label."
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def private_phase1_dir(root: Path) -> Path:
    return root.parent / f"{root.name}_private" / "phase1"


def default_queue_path(root: Path) -> Path:
    return private_phase1_dir(root) / "label_boundary_review_queue_v1.csv"


def default_output_path(root: Path) -> Path:
    return private_phase1_dir(root) / "label_boundary_review_v1_resolved.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def pair_id_from_evidence(value: str) -> str:
    pair_id = value.rsplit(":", 1)[-1]
    if pair_id not in EXPECTED_PAIR_IDS:
        raise ValueError(f"Unexpected conflict pair reference: {value}")
    return pair_id


def load_cases(root: Path, queue_path: Path) -> list[dict[str, object]]:
    if sha256(queue_path) != EXPECTED_QUEUE_SHA256:
        raise ValueError("PRIVATE BOUNDARY QUEUE HASH MISMATCH")
    queue_rows = read_csv(queue_path)
    if len(queue_rows) != 6 or len({row["sample_id"] for row in queue_rows}) != 6:
        raise ValueError("Private boundary queue must contain six unique source samples")
    queue_by_sample = {row["sample_id"]: row for row in queue_rows}

    ontology = root / "research" / "phase1" / "ontology"
    family_dir = root / "research" / "phase1" / "paraphrase_families"
    family_map_path = family_dir / "paraphrase_family_map_v1.csv"
    if sha256(family_map_path) != EXPECTED_FAMILY_MAP_SHA256:
        raise ValueError("FINAL FAMILY MAP HASH MISMATCH")
    family_by_sample = {row["sample_id"]: row for row in read_csv(family_map_path)}
    split_by_sample = {
        row["sample_id"]: row["split"]
        for row in read_csv(root / "research" / "phase0" / "nid_5class_split_manifest_v1.csv")
    }
    final_pairs = {
        row["pair_id"]: row for row in read_csv(family_dir / "final_pair_decisions_v1.csv")
    }
    conflicts = read_csv(ontology / "nid_5class_source_conflicts_v1.csv")
    contract = yaml.safe_load((ontology / "nid_5class_intent_contract_v1.yaml").read_text(encoding="utf-8"))
    definition_by_name = {row["label_name"]: row["short_definition"] for row in contract["labels"]}
    matrix = read_csv(ontology / "nid_5class_confusing_neighbor_matrix_v1.csv")
    boundary_by_labels = {
        frozenset((row["label_a"], row["label_b"])): row["main_distinction"] for row in matrix
    }

    cases: list[dict[str, object]] = []
    for number, conflict in enumerate(conflicts, start=1):
        pair_id = pair_id_from_evidence(conflict["evidence_source"])
        pair = final_pairs[pair_id]
        sample_a = conflict["sample_id_a"]
        sample_b = conflict["sample_id_b"]
        label_a = conflict["label_a"]
        label_b = conflict["label_b"]
        if {pair["sample_id_a"], pair["sample_id_b"]} != {sample_a, sample_b}:
            raise ValueError(f"Pair membership mismatch for {pair_id}")
        if queue_by_sample[sample_a]["source_label"] != label_a or queue_by_sample[sample_b]["source_label"] != label_b:
            raise ValueError(f"Private queue source labels changed for {pair_id}")
        family_a = family_by_sample[sample_a]["paraphrase_family_id"]
        family_b = family_by_sample[sample_b]["paraphrase_family_id"]
        if family_a != family_b:
            raise ValueError(f"Equivalent conflict samples are not in one family: {pair_id}")
        cases.append(
            {
                "boundary_review_id": f"NID5-LB-{number:04d}",
                "pair_id": pair_id,
                "sample_id_a": sample_a,
                "text_a": queue_by_sample[sample_a]["text"],
                "source_label_a": label_a,
                "split_a": split_by_sample[sample_a],
                "sample_id_b": sample_b,
                "text_b": queue_by_sample[sample_b]["text"],
                "source_label_b": label_b,
                "split_b": split_by_sample[sample_b],
                "paraphrase_family_id": family_a,
                "definition_a": definition_by_name[label_a],
                "definition_b": definition_by_name[label_b],
                "boundary_rule": boundary_by_labels[frozenset((label_a, label_b))],
                "existing_semantic_decision": pair["semantic_decision"],
                "existing_semantic_source": pair["semantic_decision_source"],
                "existing_family_equivalence": pair["family_equivalence"],
                "existing_family_source": pair["family_equivalence_source"],
            }
        )
    if tuple(case["pair_id"] for case in cases) != EXPECTED_PAIR_IDS:
        raise ValueError("Conflict cases are missing or out of canonical order")
    return cases


def normalize_decision(choice: str) -> str:
    value = DECISIONS.get(choice.strip(), choice.strip().upper())
    if value not in ALLOWED_DECISIONS:
        raise ValueError("Decision must be 1, 2, 3, or 4")
    return value


def build_resolved_row(
    case: dict[str, object], decision: str, notes: str = "", timestamp: str | None = None
) -> dict[str, str]:
    decision = normalize_decision(decision)
    if decision == "CANONICAL_LABEL_A":
        canonical_name = str(case["source_label_a"])
    elif decision == "CANONICAL_LABEL_B":
        canonical_name = str(case["source_label_b"])
    else:
        canonical_name = ""
    canonical_id = "" if not canonical_name else str(LABEL_IDS[canonical_name])
    return {
        "boundary_review_id": str(case["boundary_review_id"]),
        "pair_id": str(case["pair_id"]),
        "sample_id_a": str(case["sample_id_a"]),
        "text_a": str(case["text_a"]),
        "source_label_a": str(case["source_label_a"]),
        "sample_id_b": str(case["sample_id_b"]),
        "text_b": str(case["text_b"]),
        "source_label_b": str(case["source_label_b"]),
        "canonical_boundary_decision": decision,
        "canonical_label_id": canonical_id,
        "canonical_label_name": canonical_name,
        "human_notes": notes,
        "reviewer": "human",
        "review_timestamp": timestamp or datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def validate_resolved_rows(rows: Iterable[dict[str, str]], cases: list[dict[str, object]]) -> None:
    case_by_pair = {str(case["pair_id"]): case for case in cases}
    seen: set[str] = set()
    for row in rows:
        pair_id = row["pair_id"]
        if pair_id in seen or pair_id not in case_by_pair:
            raise ValueError("Duplicate or unknown resolved pair ID")
        seen.add(pair_id)
        case = case_by_pair[pair_id]
        for field in ("sample_id_a", "text_a", "source_label_a", "sample_id_b", "text_b", "source_label_b"):
            if row[field] != str(case[field]):
                raise ValueError(f"Immutable source field changed: {pair_id} {field}")
        decision = normalize_decision(row["canonical_boundary_decision"])
        expected = build_resolved_row(case, decision, row.get("human_notes", ""), row["review_timestamp"])
        if row["canonical_label_id"] != expected["canonical_label_id"] or row["canonical_label_name"] != expected["canonical_label_name"]:
            raise ValueError(f"Canonical label is invalid for {pair_id}")
        if row["reviewer"] != "human":
            raise ValueError("Reviewer must be human")


def read_resolved(path: Path, cases: list[dict[str, object]]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = read_csv(path)
    validate_resolved_rows(rows, cases)
    return rows


def save_resolved(path: Path, rows: list[dict[str, str]], cases: list[dict[str, object]]) -> None:
    validate_resolved_rows(rows, cases)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def display_case(case: dict[str, object], current: int, total: int) -> None:
    print("=" * 60)
    print(f"BOUNDARY REVIEW {current} / {total}\n")
    print(f"Conflict pair: {case['pair_id']}")
    print(f"Paraphrase family: {case['paraphrase_family_id']}\n")
    print("Sample A:")
    print(f"ID: {case['sample_id_a']}")
    print(f"Source label: {case['source_label_a']}")
    print(f"Phase 0 split: {case['split_a']}")
    print(f"Text: {case['text_a']}\n")
    print("Sample B:")
    print(f"ID: {case['sample_id_b']}")
    print(f"Source label: {case['source_label_b']}")
    print(f"Phase 0 split: {case['split_b']}")
    print(f"Text: {case['text_b']}\n")
    print("These queries already have established equivalent meaning.")
    print("Choose one canonical ontology boundary for their shared meaning.\n")
    print(f"Candidate label A: {case['source_label_a']}")
    print(f"Current definition: {case['definition_a']}\n")
    print(f"Candidate label B: {case['source_label_b']}")
    print(f"Current definition: {case['definition_b']}\n")
    print(f"Current pairwise boundary rule: {case['boundary_rule']}\n")
    print("Existing evidence:")
    print(f"Semantic decision: {case['existing_semantic_decision']} ({case['existing_semantic_source']})")
    print(f"Family relation: {case['existing_family_equivalence']} ({case['existing_family_source']})\n")
    print("Choose:")
    print("1 = CANONICAL_LABEL_A")
    print("2 = CANONICAL_LABEL_B")
    print("3 = CLARIFY_REQUIRED")
    print("4 = EXCLUDE_FROM_STRICT_BOUNDARY_EVIDENCE")
    print("S = save and exit")
    print("=" * 60)


def interactive_review(cases: list[dict[str, object]], output: Path) -> None:
    resolved = read_resolved(output, cases)
    completed = {row["pair_id"] for row in resolved}
    print("HUMAN LABEL-BOUNDARY REVIEW GUIDANCE")
    print(GUIDANCE)
    print(f"\nCompleted: {len(completed)} / {len(cases)}")
    print(f"Remaining: {len(cases) - len(completed)} / {len(cases)}\n")
    for position, case in enumerate(cases, start=1):
        if case["pair_id"] in completed:
            continue
        display_case(case, position, len(cases))
        while True:
            choice = input("Decision [1/2/3/4/S]: ").strip()
            if choice.upper() == "S":
                print(f"Completed: {len(resolved)} / {len(cases)}")
                print(f"Remaining: {len(cases) - len(resolved)} / {len(cases)}")
                return
            try:
                decision = normalize_decision(choice)
                break
            except ValueError as error:
                print(error)
        notes = input("Optional human notes (press Enter to leave blank): ").strip()
        resolved.append(build_resolved_row(case, decision, notes))
        save_resolved(output, resolved, cases)
        print("Decision saved privately.")
        print(f"Completed: {len(resolved)} / {len(cases)}")
        print(f"Remaining: {len(cases) - len(resolved)} / {len(cases)}\n")
    print("HUMAN LABEL-BOUNDARY REVIEW COMPLETE: 3 / 3")
    print(f"Private resolved file: {output}")
    print(f"SHA-256: {sha256(output)}")


def main() -> None:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=default_queue_path(root))
    parser.add_argument("--output", type=Path, default=default_output_path(root))
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and count the three cases without displaying raw text or creating output.",
    )
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Resolved raw-text output must remain outside the Git repository")
    cases = load_cases(root, args.queue)
    existing = read_resolved(args.output, cases)
    if args.validate_only:
        print("LABEL BOUNDARY REVIEW TOOL VALIDATION: PASS")
        print(f"CONFLICT CASES: {len(cases)}")
        print(f"SOURCE SAMPLES: {len({case[key] for case in cases for key in ('sample_id_a', 'sample_id_b')})}")
        print(f"HUMAN DECISIONS COMPLETED: {len(existing)} / {len(cases)}")
        return
    interactive_review(cases, args.output)


if __name__ == "__main__":
    main()
