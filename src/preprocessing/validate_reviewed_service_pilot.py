"""Validate a reviewed four-independent-seed service taxonomy and pilot."""

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import csv
import re
import sys

import yaml

from service_pilot_framework import DATASET_COLUMNS, REVIEW_COLUMNS


ALLOWED_PRIORITY = {"Low", "Medium", "High"}
ALLOWED_STYLE = {"Formal", "Informal", "Mixed"}
ALLOWED_DIFFICULTY = {"Easy", "Medium", "Hard"}
ALLOWED_EVIDENCE = {
    "official_workflow_supported", "official_service_supported",
    "needs_pilot_validation", "needs_source_review",
}
ARTIFACT_PATTERNS = [
    re.compile(r"\bnot\s+.+\bbut\b", re.I),
    re.compile(r"specifically", re.I),
    re.compile(r"\bনা[—,-].*(?:জানতে|চাই|বরং)"),
]


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("taxonomy", type=Path)
    parser.add_argument("pilot", nargs="?", type=Path)
    parser.add_argument("review", nargs="?", type=Path)
    args = parser.parse_args()
    errors = []

    taxonomy = yaml.safe_load(args.taxonomy.read_text(encoding="utf-8"))
    service = taxonomy.get("service_id")
    parents = taxonomy.get("parent_topics", {})
    prefix = taxonomy.get("id_prefix", "")
    leaves = {}
    display_names = []
    includes = []

    for parent_id, parent in parents.items():
        if not parent_id.startswith(prefix + "_"):
            errors.append(f"Parent ID has wrong prefix: {parent_id}")
        for field in ("display_name", "description", "covers", "query_topics"):
            if not parent.get(field):
                errors.append(f"{parent_id} missing/empty {field}")
        for leaf_id, leaf in parent.get("query_topics", {}).items():
            if leaf_id in leaves:
                errors.append(f"Duplicate leaf ID: {leaf_id}")
            leaves[leaf_id] = (parent_id, parent, leaf)
            display_names.append(normalize(leaf.get("display_name", "")))
            for field in ("display_name", "description", "includes", "excludes"):
                if not leaf.get(field):
                    errors.append(f"{leaf_id} missing/empty {field}")
            if leaf.get("evidence_status") not in ALLOWED_EVIDENCE:
                errors.append(f"{leaf_id} invalid evidence_status")
            includes.extend(normalize(x) for x in leaf.get("includes", []))

    if len(display_names) != len(set(display_names)):
        errors.append("Duplicate normalized leaf display names")
    if len(includes) != len(set(includes)):
        errors.append("Duplicate normalized taxonomy include examples")

    flags = taxonomy.get("freeze_status", {})
    required_flags = {
        "shared_contract_frozen", "parent_topics_reviewed",
        "query_topics_defined", "inclusion_exclusion_rules_defined",
        "semantic_audit_passed", "pilot_dataset_created",
        "taxonomy_ready_for_shared_contract",
    }
    if set(flags) != required_flags:
        errors.append("freeze_status does not contain the exact required flags")
    if not isinstance(flags.get("shared_contract_frozen"), bool):
        errors.append("shared_contract_frozen must be boolean")

    print("=" * 72)
    print(f"{service} TAXONOMY VALIDATION")
    print("=" * 72)
    print(f"Version/status: {taxonomy.get('taxonomy_version')} / {taxonomy.get('status')}")
    print(f"Parents: {len(parents)}")
    print(f"Leaves: {len(leaves)}")
    print("Leaves by parent:")
    for parent_id, parent in parents.items():
        print(f"  {parent_id}: {len(parent['query_topics'])}")

    if args.pilot is not None:
        if args.review is None:
            errors.append("Review CSV is required when validating a pilot")
        else:
            validate_pilot(args, service, leaves, errors)

    if errors:
        print(f"RESULT: FAIL ({len(errors)} issue(s))")
        for error in errors:
            print(f"ERROR: {error}")
        sys.exit(1)
    print("RESULT: PASS")
    print("Shared contract frozen:", flags.get("shared_contract_frozen"))


def validate_pilot(args, service, leaves, errors) -> None:
    header, rows = read_csv(args.pilot)
    review_header, reviews = read_csv(args.review)
    expected_rows = len(leaves) * 4
    if header != DATASET_COLUMNS:
        errors.append("Pilot schema does not exactly match canonical schema")
    if review_header != DATASET_COLUMNS + REVIEW_COLUMNS:
        errors.append("Review schema does not match expected review schema")
    if len(rows) != expected_rows or len(reviews) != expected_rows:
        errors.append(
            f"Expected {expected_rows} pilot/review rows, found {len(rows)}/{len(reviews)}"
        )

    ids = [row.get("id", "") for row in rows]
    texts = [normalize(row.get("text", "")) for row in rows]
    families = [row.get("parent_query_id", "") for row in rows]
    if len(set(ids)) != expected_rows:
        errors.append("Row IDs are not unique")
    if len(set(texts)) != expected_rows:
        errors.append("Normalized query texts are not unique")
    if len(set(families)) != expected_rows:
        errors.append("Pilot family IDs are not unique")

    topic_counts = Counter()
    parent_counts = Counter()
    priority_counts = Counter()
    style_counts = Counter()
    difficulty_counts = Counter()
    artifact_rows = []
    for row in rows:
        leaf_id = row.get("query_topic_id", "")
        topic_counts[leaf_id] += 1
        parent_counts[row.get("parent_topic_id", "")] += 1
        priority_counts[row.get("priority", "")] += 1
        style_counts[row.get("language_style", "")] += 1
        difficulty_counts[row.get("difficulty", "")] += 1
        if row.get("service") != service:
            errors.append(f"{row.get('id')}: wrong service")
        if leaf_id not in leaves:
            errors.append(f"{row.get('id')}: unknown leaf {leaf_id}")
            continue
        parent_id, parent, leaf = leaves[leaf_id]
        if row.get("parent_topic_id") != parent_id:
            errors.append(f"{row.get('id')}: wrong parent ID")
        if row.get("parent_topic") != parent["display_name"]:
            errors.append(f"{row.get('id')}: wrong parent name")
        if row.get("query_topic") != leaf["display_name"]:
            errors.append(f"{row.get('id')}: wrong leaf name")
        if row.get("priority") not in ALLOWED_PRIORITY:
            errors.append(f"{row.get('id')}: invalid priority")
        if row.get("language_style") not in ALLOWED_STYLE:
            errors.append(f"{row.get('id')}: invalid language style")
        if row.get("difficulty") not in ALLOWED_DIFFICULTY:
            errors.append(f"{row.get('id')}: invalid difficulty")
        if row.get("source_type") != "SYNTHETIC":
            errors.append(f"{row.get('id')}: source must be SYNTHETIC")
        if row.get("privacy_present") != "FALSE" or row.get("privacy_types"):
            errors.append(f"{row.get('id')}: invalid privacy fields")
        if row.get("is_ood") != "FALSE":
            errors.append(f"{row.get('id')}: pilot must be in-domain")
        if not re.fullmatch(re.escape(leaf_id) + r"_F0[1-4]", row.get("parent_query_id", "")):
            errors.append(f"{row.get('id')}: invalid family ID")
        if any(pattern.search(row.get("text", "")) for pattern in ARTIFACT_PATTERNS):
            artifact_rows.append(row.get("id"))

    if set(topic_counts) != set(leaves):
        errors.append("Pilot does not cover every taxonomy leaf exactly")
    wrong_counts = {key: value for key, value in topic_counts.items() if value != 4}
    if wrong_counts:
        errors.append(f"Every leaf must have four rows: {wrong_counts}")
    if artifact_rows:
        errors.append(f"Annotation-engineered contrast patterns found: {artifact_rows}")

    pilot_by_id = {row["id"]: row for row in rows}
    decisions = Counter()
    review_groups = Counter()
    for review in reviews:
        row_id = review.get("id", "")
        decisions[review.get("review_decision", "")] += 1
        review_groups[review.get("review_priority", "")] += 1
        if row_id not in pilot_by_id:
            errors.append(f"Review has unknown row ID: {row_id}")
            continue
        if review.get("text") != pilot_by_id[row_id].get("text"):
            errors.append(f"{row_id}: review/canonical text mismatch")
        required_yes = [
            "natural_query", "service_context_clear", "parent_label_correct",
            "query_topic_correct", "language_style_correct", "priority_correct",
            "difficulty_correct", "independent_seed", "mutable_fact_safe",
            "privacy_safe", "retain_leaf",
        ]
        if any(review.get(column) != "YES" for column in required_yes):
            errors.append(f"{row_id}: semantic review has unresolved field")
        if review.get("more_specific_leaf_available") != "NO":
            errors.append(f"{row_id}: more-specific leaf remains available")
        if review.get("review_decision") not in {"PASS", "REWRITE"}:
            errors.append(f"{row_id}: unresolved review decision")
        if not review.get("review_notes"):
            errors.append(f"{row_id}: missing review notes")

    print("Pilot rows/families:", len(rows), "/", len(set(families)))
    print("Priority:", dict(priority_counts))
    print("Language style:", dict(style_counts))
    print("Difficulty:", dict(difficulty_counts))
    print("Review groups:", dict(review_groups))
    print("Review decisions:", dict(decisions))
    print("Annotation-engineered pattern hits:", len(artifact_rows))


if __name__ == "__main__":
    main()
