from pathlib import Path
from collections import Counter, defaultdict
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is not installed.")
    print("Run: python -m pip install pyyaml")
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = ROOT / "taxonomy" / "nid.yaml"

ALLOWED_EVIDENCE_STATUS = {
    "supported_by_current_dataset",
    "needs_pilot_expansion",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def construct_unique_mapping(loader, node, deep=False):
    mapping = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)

        if key in mapping:
            raise ValueError(f"Duplicate YAML key detected: {key}")

        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value

    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def load_taxonomy():
    text = TAXONOMY_PATH.read_text(encoding="utf-8")
    return yaml.load(text, Loader=UniqueKeyLoader)


def main():
    errors = []
    warnings = []

    try:
        data = load_taxonomy()
    except Exception as exc:
        print(f"FAILED TO PARSE: {exc}")
        sys.exit(1)

    if data.get("service_id") != "NID":
        errors.append(
            f"service_id must be NID, found: {data.get('service_id')!r}"
        )

    parents = data.get("parent_topics")

    if not isinstance(parents, dict) or not parents:
        errors.append("parent_topics must be a non-empty mapping.")
        parents = {}

    leaf_locations = defaultdict(list)
    display_names = defaultdict(list)
    include_examples = defaultdict(list)

    missing_evidence = []
    missing_excludes = []
    missing_includes = []

    total_leaves = 0

    required_parent_fields = {
        "display_name",
        "description",
        "covers",
        "query_topics",
    }

    required_leaf_fields = {
        "display_name",
        "description",
        "includes",
        "excludes",
        "evidence_status",
    }

    for parent_id, parent in parents.items():

        if not parent_id.startswith("NID_"):
            errors.append(
                f"Parent ID does not start with NID_: {parent_id}"
            )

        if not isinstance(parent, dict):
            errors.append(f"{parent_id} must contain a mapping.")
            continue

        for field in required_parent_fields:
            if field not in parent:
                errors.append(
                    f"{parent_id} missing required field: {field}"
                )

        query_topics = parent.get("query_topics", {})

        if not isinstance(query_topics, dict) or not query_topics:
            errors.append(
                f"{parent_id} has no query topics."
            )
            continue

        for query_id, query in query_topics.items():
            total_leaves += 1
            leaf_locations[query_id].append(parent_id)

            if not query_id.startswith("NID_"):
                errors.append(
                    f"Query-topic ID does not start with NID_: {query_id}"
                )

            if not isinstance(query, dict):
                errors.append(
                    f"{query_id} must contain a mapping."
                )
                continue

            display_name = query.get("display_name")

            if display_name:
                display_names[display_name].append(query_id)

            for field in required_leaf_fields:
                if field not in query:
                    if field == "evidence_status":
                        missing_evidence.append(query_id)
                    elif field == "excludes":
                        missing_excludes.append(query_id)
                    elif field == "includes":
                        missing_includes.append(query_id)
                    else:
                        errors.append(
                            f"{query_id} missing required field: {field}"
                        )

            evidence_status = query.get("evidence_status")

            if (
                evidence_status is not None
                and evidence_status not in ALLOWED_EVIDENCE_STATUS
            ):
                errors.append(
                    f"{query_id} has invalid evidence_status: "
                    f"{evidence_status!r}"
                )

            for example in query.get("includes", []) or []:
                normalized = str(example).strip().lower()
                include_examples[normalized].append(
                    (parent_id, query_id)
                )

    duplicate_ids = {
        query_id: locations
        for query_id, locations in leaf_locations.items()
        if len(locations) > 1
    }

    for query_id, locations in duplicate_ids.items():
        errors.append(
            f"Query-topic ID appears under multiple parents: "
            f"{query_id} -> {locations}"
        )

    duplicate_names = {
        name: ids
        for name, ids in display_names.items()
        if len(ids) > 1
    }

    for name, ids in duplicate_names.items():
        warnings.append(
            f"Duplicate display name {name!r}: {ids}"
        )

    duplicate_examples = {
        example: locations
        for example, locations in include_examples.items()
        if len(locations) > 1
    }

    for example, locations in duplicate_examples.items():
        warnings.append(
            f"Same include example appears in multiple leaves: "
            f"{example!r} -> {locations}"
        )

    source_mapping = data.get("source_dataset_mapping", {})

    for source_label, mapping in source_mapping.items():
        primary_parent = mapping.get("primary_parent")

        if primary_parent not in parents:
            errors.append(
                f"source_dataset_mapping {source_label!r} references "
                f"unknown parent: {primary_parent!r}"
            )

    freeze_status = data.get("freeze_status", {})

    print("=" * 72)
    print("NAGORIKSHEBA AI — NID TAXONOMY AUDIT")
    print("=" * 72)
    print(f"File: {TAXONOMY_PATH}")
    print(f"Taxonomy version: {data.get('taxonomy_version')}")
    print(f"Service: {data.get('service_id')}")
    print(f"Parents: {len(parents)}")
    print(f"Query topics: {total_leaves}")
    print()

    print("QUERY TOPICS PER PARENT")
    print("-" * 72)

    for parent_id, parent in parents.items():
        count = len(parent.get("query_topics", {}))
        print(f"{parent_id}: {count}")

    print()
    print("CONSISTENCY FINDINGS")
    print("-" * 72)

    print(
        f"Missing evidence_status: {len(missing_evidence)}"
    )

    for query_id in missing_evidence:
        print(f"  - {query_id}")

    print()
    print(
        f"Missing excludes: {len(missing_excludes)}"
    )

    for query_id in missing_excludes:
        print(f"  - {query_id}")

    print()
    print(
        f"Missing includes: {len(missing_includes)}"
    )

    for query_id in missing_includes:
        print(f"  - {query_id}")

    print()
    print(f"Duplicate query-topic IDs: {len(duplicate_ids)}")
    print(f"Duplicate display names: {len(duplicate_names)}")
    print()

    print("FREEZE STATUS")
    print("-" * 72)

    for key, value in freeze_status.items():
        print(f"{key}: {value}")

    print()

    if warnings:
        print("WARNINGS")
        print("-" * 72)

        for warning in warnings:
            print(f"WARNING: {warning}")

        print()

    if missing_evidence:
        errors.append(
            f"{len(missing_evidence)} query topics are missing evidence_status."
        )

    if missing_excludes:
        errors.append(
            f"{len(missing_excludes)} query topics are missing excludes."
        )

    if missing_includes:
        errors.append(
            f"{len(missing_includes)} query topics are missing includes."
        )

    print("FINAL RESULT")
    print("-" * 72)

    if errors:
        print("STATUS: NOT READY TO FREEZE")
        print()

        for error in errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print("STATUS: STRUCTURAL AUDIT PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
