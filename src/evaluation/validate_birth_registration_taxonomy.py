from pathlib import Path
from collections import defaultdict
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is not installed.")
    print("Run: python -m pip install pyyaml")
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = ROOT / "taxonomy" / "birth_registration.yaml"

EXPECTED_SERVICE_ID = "BIRTH_REGISTRATION"
EXPECTED_ID_PREFIX = "BR_"

ALLOWED_EVIDENCE_STATUS = {
    "official_workflow_supported",
    "official_service_supported",
    "official_fee_service_supported",
    "needs_query_pilot",
    "needs_source_review",
}

REQUIRED_FREEZE_FLAGS = {
    "shared_contract_frozen",
    "parent_topics_reviewed",
    "query_topics_defined",
    "inclusion_exclusion_rules_defined",
    "semantic_audit_passed",
    "pilot_dataset_created",
    "taxonomy_ready_for_shared_contract",
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

    if not isinstance(data, dict):
        print("FAILED TO PARSE: taxonomy root must be a mapping.")
        sys.exit(1)

    if data.get("service_id") != EXPECTED_SERVICE_ID:
        errors.append(
            f"service_id must be {EXPECTED_SERVICE_ID}, "
            f"found: {data.get('service_id')!r}"
        )

    if data.get("id_prefix") != "BR":
        errors.append(
            f"id_prefix must be 'BR', found: {data.get('id_prefix')!r}"
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
    empty_includes = []
    empty_excludes = []

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
    }

    for parent_id, parent in parents.items():

        if not parent_id.startswith(EXPECTED_ID_PREFIX):
            errors.append(
                f"Parent ID does not start with "
                f"{EXPECTED_ID_PREFIX}: {parent_id}"
            )

        if not isinstance(parent, dict):
            errors.append(f"{parent_id} must contain a mapping.")
            continue

        for field in required_parent_fields:
            if field not in parent:
                errors.append(
                    f"{parent_id} missing required field: {field}"
                )

        default_evidence_status = parent.get(
            "default_evidence_status"
        )

        if default_evidence_status is None:
            missing_evidence.append(parent_id)

        elif default_evidence_status not in ALLOWED_EVIDENCE_STATUS:
            errors.append(
                f"{parent_id} has invalid default_evidence_status: "
                f"{default_evidence_status!r}"
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

            if not query_id.startswith(EXPECTED_ID_PREFIX):
                errors.append(
                    f"Query-topic ID does not start with "
                    f"{EXPECTED_ID_PREFIX}: {query_id}"
                )

            if not isinstance(query, dict):
                errors.append(
                    f"{query_id} must contain a mapping."
                )
                continue

            display_name = query.get("display_name")

            if display_name:
                display_names[
                    display_name.strip().lower()
                ].append(query_id)

            for field in required_leaf_fields:
                if field not in query:
                    if field == "excludes":
                        missing_excludes.append(query_id)

                    elif field == "includes":
                        missing_includes.append(query_id)

                    else:
                        errors.append(
                            f"{query_id} missing required field: "
                            f"{field}"
                        )

            includes = query.get("includes")
            excludes = query.get("excludes")

            if "includes" in query and (
                not isinstance(includes, list)
                or len(includes) == 0
            ):
                empty_includes.append(query_id)

            if "excludes" in query and (
                not isinstance(excludes, list)
                or len(excludes) == 0
            ):
                empty_excludes.append(query_id)

            evidence_status = query.get(
                "evidence_status",
                default_evidence_status,
            )

            if evidence_status is None:
                missing_evidence.append(query_id)

            elif evidence_status not in ALLOWED_EVIDENCE_STATUS:
                errors.append(
                    f"{query_id} has invalid evidence_status: "
                    f"{evidence_status!r}"
                )

            for example in includes or []:
                normalized = " ".join(
                    str(example).lower().split()
                )

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

    freeze_status = data.get("freeze_status")

    if not isinstance(freeze_status, dict):
        errors.append("freeze_status must be a mapping.")
        freeze_status = {}

    missing_freeze_flags = sorted(
        REQUIRED_FREEZE_FLAGS - set(freeze_status.keys())
    )

    for flag in missing_freeze_flags:
        errors.append(
            f"freeze_status missing required flag: {flag}"
        )

    for flag, value in freeze_status.items():
        if (
            flag in REQUIRED_FREEZE_FLAGS
            and not isinstance(value, bool)
        ):
            errors.append(
                f"freeze_status.{flag} must be boolean, "
                f"found: {value!r}"
            )

    print("=" * 72)
    print(
        "NAGORIKSHEBA AI — "
        "BIRTH REGISTRATION TAXONOMY AUDIT"
    )
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
    print(
        f"Missing includes: {len(missing_includes)}"
    )
    print(
        f"Missing excludes: {len(missing_excludes)}"
    )
    print(
        f"Empty includes: {len(empty_includes)}"
    )
    print(
        f"Empty excludes: {len(empty_excludes)}"
    )
    print(
        f"Duplicate query-topic IDs: {len(duplicate_ids)}"
    )
    print(
        f"Duplicate display names: {len(duplicate_names)}"
    )
    print(
        f"Duplicate include examples: "
        f"{len(duplicate_examples)}"
    )

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
            f"{len(missing_evidence)} parent/query topics are "
            "missing an effective evidence_status."
        )

    if missing_includes:
        errors.append(
            f"{len(missing_includes)} query topics are "
            "missing includes."
        )

    if missing_excludes:
        errors.append(
            f"{len(missing_excludes)} query topics are "
            "missing excludes."
        )

    if empty_includes:
        errors.append(
            f"{len(empty_includes)} query topics have "
            "empty/invalid includes."
        )

    if empty_excludes:
        errors.append(
            f"{len(empty_excludes)} query topics have "
            "empty/invalid excludes."
        )

    print("FINAL RESULT")
    print("-" * 72)

    if errors:
        print("STATUS: STRUCTURAL AUDIT FAILED")
        print()

        for error in errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print("STATUS: STRUCTURAL AUDIT PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
