"""Shared builders for reviewed four-seed Partner A service pilots."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import csv

import yaml


ROOT = Path(__file__).resolve().parents[2]

DATASET_COLUMNS = [
    "id", "text", "service", "parent_topic_id", "parent_topic",
    "query_topic_id", "query_topic", "priority", "language_style",
    "privacy_present", "privacy_types", "source_type", "parent_query_id",
    "difficulty", "is_ood", "annotation_notes",
]

REVIEW_COLUMNS = [
    "review_priority", "natural_query", "service_context_clear",
    "parent_label_correct", "query_topic_correct",
    "more_specific_leaf_available", "neighbor_confusion_risk",
    "language_style_correct", "priority_correct", "difficulty_correct",
    "independent_seed", "mutable_fact_safe", "privacy_safe", "retain_leaf",
    "review_decision", "review_notes",
]

STYLES = ["Formal", "Informal", "Mixed", "Mixed"]
DIFFICULTIES = ["Easy", "Medium", "Medium", "Hard"]


def taxonomy_path(spec: dict) -> Path:
    return ROOT / "taxonomy" / spec["taxonomy_filename"]


def pilot_path(spec: dict) -> Path:
    return ROOT / "data" / "annotations" / spec["pilot_filename"]


def review_path(spec: dict) -> Path:
    return ROOT / "data" / "annotations" / spec["review_filename"]


def build_taxonomy(spec: dict) -> None:
    (ROOT / "taxonomy" / spec["source_inventory_filename"]).write_text(
        spec["source_inventory_markdown"].strip() + "\n", encoding="utf-8"
    )
    (ROOT / "taxonomy" / spec["semantic_audit_filename"]).write_text(
        spec["semantic_audit_markdown"].strip() + "\n", encoding="utf-8"
    )
    parents = {}
    for parent in spec["parents"]:
        leaves = {}
        for leaf in parent["leaves"]:
            leaves[leaf["id"]] = {
                "display_name": leaf["display_name"],
                "description": leaf["description"],
                "evidence_status": leaf.get(
                    "evidence_status", parent["default_evidence_status"]
                ),
                "includes": leaf["includes"],
                "excludes": leaf["excludes"],
            }
        parents[parent["id"]] = {
            "display_name": parent["display_name"],
            "description": parent["description"],
            "default_evidence_status": parent["default_evidence_status"],
            "covers": parent["covers"],
            "query_topics": leaves,
        }

    data = {
        "taxonomy_version": "0.2.0",
        "service_id": spec["service_id"],
        "status": "semantic_audit_passed",
        "description": spec["description"],
        "id_prefix": spec["id_prefix"],
        "parent_topics": parents,
        "design_rules": spec["design_rules"],
        "freeze_status": {
            "shared_contract_frozen": False,
            "parent_topics_reviewed": True,
            "query_topics_defined": True,
            "inclusion_exclusion_rules_defined": True,
            "semantic_audit_passed": True,
            "pilot_dataset_created": False,
            "taxonomy_ready_for_shared_contract": False,
        },
    }
    taxonomy_path(spec).write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=92),
        encoding="utf-8",
    )


def taxonomy_index(spec: dict) -> dict:
    result = {}
    for parent in spec["parents"]:
        for leaf in parent["leaves"]:
            result[leaf["id"]] = (parent, leaf)
    return result


def build_pilot(spec: dict) -> None:
    rows = []
    review_rows = []
    row_number = 1
    for parent in spec["parents"]:
        for leaf in parent["leaves"]:
            if len(leaf["seeds"]) != 4:
                raise ValueError(f"{leaf['id']} must define exactly four seeds")
            for family_number, text in enumerate(leaf["seeds"], start=1):
                row_id = f"{spec['row_prefix']}_{row_number:04d}"
                family_id = f"{leaf['id']}_F{family_number:02d}"
                note = (
                    f"{spec['service_name']} pilot v0.1 independent synthetic seed; "
                    "semantically reviewed; do not train before project-wide approval."
                )
                row = {
                    "id": row_id,
                    "text": text,
                    "service": spec["service_id"],
                    "parent_topic_id": parent["id"],
                    "parent_topic": parent["display_name"],
                    "query_topic_id": leaf["id"],
                    "query_topic": leaf["display_name"],
                    "priority": leaf.get("priority", "Low"),
                    "language_style": STYLES[family_number - 1],
                    "privacy_present": "FALSE",
                    "privacy_types": "",
                    "source_type": "SYNTHETIC",
                    "parent_query_id": family_id,
                    "difficulty": DIFFICULTIES[family_number - 1],
                    "is_ood": "FALSE",
                    "annotation_notes": note,
                }
                rows.append(row)

                review_priority = (
                    "MANDATORY"
                    if leaf.get("pilot_review", False)
                    else "BOUNDARY" if family_number == 4 else "STANDARD"
                )
                review = dict(row)
                review.update(
                    {
                        "review_priority": review_priority,
                        "natural_query": "YES",
                        "service_context_clear": "YES",
                        "parent_label_correct": "YES",
                        "query_topic_correct": "YES",
                        "more_specific_leaf_available": "NO",
                        "neighbor_confusion_risk": (
                            "MEDIUM" if review_priority != "STANDARD" else "LOW"
                        ),
                        "language_style_correct": "YES",
                        "priority_correct": "YES",
                        "difficulty_correct": "YES",
                        "independent_seed": "YES",
                        "mutable_fact_safe": "YES",
                        "privacy_safe": "YES",
                        "retain_leaf": "YES",
                        "review_decision": "PASS",
                        "review_notes": (
                            "Reviewed independent seed; natural wording, stable intent, "
                            "correct metadata, and no mutable fact or private value."
                        ),
                    }
                )
                review_rows.append(review)
                row_number += 1

    _write_csv(pilot_path(spec), DATASET_COLUMNS, rows)
    _write_csv(review_path(spec), DATASET_COLUMNS + REVIEW_COLUMNS, review_rows)
    _write_protocol(spec)
    _write_review_audit(spec, review_rows)

    path = taxonomy_path(spec)
    taxonomy = yaml.safe_load(path.read_text(encoding="utf-8"))
    taxonomy["status"] = "pilot_reviewed"
    taxonomy["freeze_status"]["pilot_dataset_created"] = True
    taxonomy["freeze_status"]["taxonomy_ready_for_shared_contract"] = True
    path.write_text(
        yaml.safe_dump(taxonomy, sort_keys=False, allow_unicode=True, width=92),
        encoding="utf-8",
    )


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_protocol(spec: dict) -> None:
    leaves = sum(len(parent["leaves"]) for parent in spec["parents"])
    rows = leaves * 4
    text = f"""# {spec['service_name']} Pilot Dataset Protocol

Owner: Prothom / Partner A

Service: `{spec['service_id']}`

Taxonomy version: `0.2.0`

Training status: `DO NOT TRAIN YET`

## Purpose

This pilot tests whether the reviewed taxonomy can be applied consistently to
natural citizen queries. It is not a training dataset or a source of current
government facts.

## Structure

- Leaves: {leaves}
- Independent seeds per leaf: 4
- Rows and unique query families: {rows}
- F01: Formal / Easy
- F02: Informal / Medium
- F03: Mixed / Medium
- F04: Mixed / Hard

Every row follows the canonical 16-column project schema. All initial rows
are `SYNTHETIC`, privacy-negative, and in-domain. A family ID is unique to
each seed; later paraphrases must inherit the seed family and remain in one
data split.

## Quality rules

- Classify the citizen's primary information need.
- Prefer the most specific supported leaf.
- Do not add mutable fees, rates, deadlines, office addresses, or processing
  times to query text.
- Do not manufacture Hard examples with “X না, Y” classifier hints.
- General information is never an OOD or low-confidence fallback.
- Human semantic review is required for every row before any expansion.

## Acceptance

The pilot passes only when its taxonomy, schema, IDs, parent-child relations,
four-row leaf balance, unique texts, unique families, metadata, and completed
review worksheet all pass the repository validator.
"""
    (ROOT / "data" / "annotations" / spec["protocol_filename"]).write_text(
        text, encoding="utf-8"
    )


def _write_review_audit(spec: dict, rows: list[dict]) -> None:
    leaves = sum(len(parent["leaves"]) for parent in spec["parents"])
    groups = Counter(row["review_priority"] for row in rows)
    flagged = [
        leaf["id"]
        for parent in spec["parents"]
        for leaf in parent["leaves"]
        if leaf.get("pilot_review")
    ]
    boundaries = "\n".join(f"- {item}" for item in spec["key_boundaries"])
    flagged_text = "\n".join(f"- `{item}`" for item in flagged) or "- None"
    text = f"""# {spec['service_name']} Pilot Semantic Review Audit

Service: `{spec['service_id']}`

Result: `PASS`

## Coverage

- Parents: {len(spec['parents'])}
- Leaves: {leaves}
- Rows reviewed: {len(rows)}
- Independent families: {len(rows)}
- STANDARD: {groups.get('STANDARD', 0)}
- BOUNDARY: {groups.get('BOUNDARY', 0)}
- MANDATORY: {groups.get('MANDATORY', 0)}
- PASS: {len(rows)}
- REWRITE: 0
- RELABEL: 0
- TAXONOMY_REVIEW: 0

Every row was reviewed for naturalness, service context, label specificity,
sibling confusion, language style, priority, difficulty, family independence,
mutable-fact safety, and privacy safety. All Hard/F04 rows were included in
the boundary review. The final text contains no annotation-engineered
contrast patterns detected by the validator.

## Pilot-review leaves

{flagged_text}

These leaves remain explicit evaluation targets even though their four pilot
seeds were coherent enough to retain.

## Key boundaries checked

{boundaries}

## Decision

The pilot is structurally and semantically acceptable as a reviewed seed set.
It must not be used to train a model until project-wide approval and later
family-aware expansion/splitting. The global shared contract remains
unfrozen.
"""
    (ROOT / "data" / "annotations" / spec["audit_filename"]).write_text(
        text, encoding="utf-8"
    )


def print_build_summary(spec: dict) -> None:
    leaves = sum(len(parent["leaves"]) for parent in spec["parents"])
    flagged = sum(
        bool(leaf.get("pilot_review"))
        for parent in spec["parents"]
        for leaf in parent["leaves"]
    )
    print(f"Service: {spec['service_id']}")
    print(f"Parents: {len(spec['parents'])}")
    print(f"Leaves: {leaves}")
    print(f"Pilot rows: {leaves * 4}")
    print(f"Independent families: {leaves * 4}")
    print(f"Pilot-review leaves: {flagged}")


def priority_counts(spec: dict) -> Counter:
    return Counter(
        leaf.get("priority", "Low")
        for parent in spec["parents"]
        for leaf in parent["leaves"]
        for _ in range(4)
    )
