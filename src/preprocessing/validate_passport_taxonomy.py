from pathlib import Path
import sys

import yaml


TAXONOMY_PATH = Path("taxonomy/passport.yaml")

EXPECTED_SERVICE_ID = "PASSPORT"
EXPECTED_ID_PREFIX = "PASS"
EXPECTED_VERSION = "0.2.0"
EXPECTED_STATUS = "contract_frozen"

EXPECTED_PARENTS = {
    "PASSPORT_APPLICATION",
    "PASSPORT_DOCUMENTS",
    "PASSPORT_ONLINE_ACCOUNT",
    "PASSPORT_APPOINTMENT_AND_ENROLMENT",
    "PASSPORT_REISSUE",
    "PASSPORT_FEES_AND_PAYMENT",
    "PASSPORT_STATUS_AND_DELIVERY",
    "PASSPORT_GENERAL_INFORMATION",
}

EXPECTED_LEAF_COUNTS = {
    "PASSPORT_APPLICATION": 7,
    "PASSPORT_DOCUMENTS": 8,
    "PASSPORT_ONLINE_ACCOUNT": 8,
    "PASSPORT_APPOINTMENT_AND_ENROLMENT": 7,
    "PASSPORT_REISSUE": 8,
    "PASSPORT_FEES_AND_PAYMENT": 8,
    "PASSPORT_STATUS_AND_DELIVERY": 7,
    "PASSPORT_GENERAL_INFORMATION": 3,
}

EXPECTED_TOTAL_LEAVES = 56

REQUIRED_TOP_LEVEL_KEYS = {
    "taxonomy_version",
    "service_id",
    "status",
    "description",
    "id_prefix",
    "parent_topics",
    "design_rules",
    "evidence_notes",
    "freeze_status",
}

REQUIRED_PARENT_KEYS = {
    "display_name",
    "description",
    "default_evidence_status",
    "covers",
    "query_topics",
}

REQUIRED_LEAF_KEYS = {
    "display_name",
    "description",
    "evidence_status",
    "includes",
    "excludes",
}

EXPECTED_FREEZE_STATUS = {
    "shared_contract_frozen": True,
    "parent_topics_reviewed": True,
    "query_topics_defined": True,
    "inclusion_exclusion_rules_defined": True,
    "semantic_audit_passed": True,
    "pilot_dataset_created": True,
    "taxonomy_ready_for_shared_contract": True,
}


def fail(errors, message):
    errors.append(message)


def normalized_text(value):
    return " ".join(str(value).strip().lower().split())


def validate_non_empty_string(errors, value, location):
    if not isinstance(value, str) or not value.strip():
        fail(errors, f"{location} must be a non-empty string.")


def validate_non_empty_list(errors, value, location):
    if not isinstance(value, list):
        fail(errors, f"{location} must be a list.")
        return

    if not value:
        fail(errors, f"{location} must not be empty.")
        return

    for index, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item.strip():
            fail(
                errors,
                f"{location}[{index}] must be a non-empty string.",
            )


def validate_example_duplicates(errors, examples, location):
    if not isinstance(examples, list):
        return

    normalized = [normalized_text(item) for item in examples if isinstance(item, str)]

    if len(normalized) != len(set(normalized)):
        fail(errors, f"{location} contains duplicate examples.")


def main():
    errors = []

    if not TAXONOMY_PATH.exists():
        print(f"ERROR: taxonomy file not found: {TAXONOMY_PATH}")
        sys.exit(1)

    try:
        with TAXONOMY_PATH.open("r", encoding="utf-8") as file:
            taxonomy = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        print("ERROR: passport.yaml is not valid YAML.")
        print(exc)
        sys.exit(1)

    if not isinstance(taxonomy, dict):
        print("ERROR: taxonomy root must be a YAML mapping.")
        sys.exit(1)

    # ---------------------------------------------------------
    # Top-level structure
    # ---------------------------------------------------------

    missing_top_level = REQUIRED_TOP_LEVEL_KEYS - set(taxonomy.keys())

    if missing_top_level:
        fail(
            errors,
            "Missing top-level keys: "
            + ", ".join(sorted(missing_top_level)),
        )

    if taxonomy.get("taxonomy_version") != EXPECTED_VERSION:
        fail(
            errors,
            f"taxonomy_version must be {EXPECTED_VERSION!r}, "
            f"found {taxonomy.get('taxonomy_version')!r}.",
        )

    if taxonomy.get("service_id") != EXPECTED_SERVICE_ID:
        fail(
            errors,
            f"service_id must be {EXPECTED_SERVICE_ID!r}, "
            f"found {taxonomy.get('service_id')!r}.",
        )

    if taxonomy.get("id_prefix") != EXPECTED_ID_PREFIX:
        fail(
            errors,
            f"id_prefix must be {EXPECTED_ID_PREFIX!r}, "
            f"found {taxonomy.get('id_prefix')!r}.",
        )

    if taxonomy.get("status") != EXPECTED_STATUS:
        fail(
            errors,
            f"status must be {EXPECTED_STATUS!r}, "
            f"found {taxonomy.get('status')!r}.",
        )

    validate_non_empty_string(
        errors,
        taxonomy.get("description"),
        "description",
    )

    # ---------------------------------------------------------
    # Parent topics
    # ---------------------------------------------------------

    parents = taxonomy.get("parent_topics")

    if not isinstance(parents, dict):
        fail(errors, "parent_topics must be a mapping.")
        parents = {}

    actual_parent_ids = set(parents.keys())

    missing_parents = EXPECTED_PARENTS - actual_parent_ids
    unexpected_parents = actual_parent_ids - EXPECTED_PARENTS

    if missing_parents:
        fail(
            errors,
            "Missing expected parent topics: "
            + ", ".join(sorted(missing_parents)),
        )

    if unexpected_parents:
        fail(
            errors,
            "Unexpected parent topics: "
            + ", ".join(sorted(unexpected_parents)),
        )

    all_leaf_ids = []
    leaf_count_by_parent = {}

    for parent_id, parent in parents.items():
        location = f"parent_topics.{parent_id}"

        if not isinstance(parent, dict):
            fail(errors, f"{location} must be a mapping.")
            continue

        missing_parent_keys = REQUIRED_PARENT_KEYS - set(parent.keys())

        if missing_parent_keys:
            fail(
                errors,
                f"{location} missing keys: "
                + ", ".join(sorted(missing_parent_keys)),
            )

        validate_non_empty_string(
            errors,
            parent.get("display_name"),
            f"{location}.display_name",
        )

        validate_non_empty_string(
            errors,
            parent.get("description"),
            f"{location}.description",
        )

        validate_non_empty_string(
            errors,
            parent.get("default_evidence_status"),
            f"{location}.default_evidence_status",
        )

        validate_non_empty_list(
            errors,
            parent.get("covers"),
            f"{location}.covers",
        )

        query_topics = parent.get("query_topics")

        if not isinstance(query_topics, dict):
            fail(errors, f"{location}.query_topics must be a mapping.")
            query_topics = {}

        if not query_topics:
            fail(errors, f"{location}.query_topics must not be empty.")

        leaf_count_by_parent[parent_id] = len(query_topics)

        expected_count = EXPECTED_LEAF_COUNTS.get(parent_id)

        if (
            expected_count is not None
            and len(query_topics) != expected_count
        ):
            fail(
                errors,
                f"{parent_id} must contain {expected_count} leaves, "
                f"found {len(query_topics)}.",
            )

        for leaf_id, leaf in query_topics.items():
            leaf_location = f"{location}.query_topics.{leaf_id}"

            all_leaf_ids.append(leaf_id)

            if not isinstance(leaf_id, str) or not leaf_id.startswith(
                "PASSPORT_"
            ):
                fail(
                    errors,
                    f"{leaf_location}: leaf ID must start with 'PASSPORT_'.",
                )

            if not isinstance(leaf, dict):
                fail(errors, f"{leaf_location} must be a mapping.")
                continue

            missing_leaf_keys = REQUIRED_LEAF_KEYS - set(leaf.keys())

            if missing_leaf_keys:
                fail(
                    errors,
                    f"{leaf_location} missing keys: "
                    + ", ".join(sorted(missing_leaf_keys)),
                )

            validate_non_empty_string(
                errors,
                leaf.get("display_name"),
                f"{leaf_location}.display_name",
            )

            validate_non_empty_string(
                errors,
                leaf.get("description"),
                f"{leaf_location}.description",
            )

            validate_non_empty_string(
                errors,
                leaf.get("evidence_status"),
                f"{leaf_location}.evidence_status",
            )

            validate_non_empty_list(
                errors,
                leaf.get("includes"),
                f"{leaf_location}.includes",
            )

            validate_non_empty_list(
                errors,
                leaf.get("excludes"),
                f"{leaf_location}.excludes",
            )

            validate_example_duplicates(
                errors,
                leaf.get("includes"),
                f"{leaf_location}.includes",
            )

            validate_example_duplicates(
                errors,
                leaf.get("excludes"),
                f"{leaf_location}.excludes",
            )

            includes = leaf.get("includes")
            excludes = leaf.get("excludes")

            if isinstance(includes, list) and isinstance(excludes, list):
                normalized_includes = {
                    normalized_text(item)
                    for item in includes
                    if isinstance(item, str)
                }

                normalized_excludes = {
                    normalized_text(item)
                    for item in excludes
                    if isinstance(item, str)
                }

                overlap = normalized_includes & normalized_excludes

                if overlap:
                    fail(
                        errors,
                        f"{leaf_location} has examples appearing in both "
                        f"includes and excludes: {sorted(overlap)}",
                    )

    # ---------------------------------------------------------
    # Global leaf checks
    # ---------------------------------------------------------

    if len(all_leaf_ids) != EXPECTED_TOTAL_LEAVES:
        fail(
            errors,
            f"Expected {EXPECTED_TOTAL_LEAVES} total query-topic leaves, "
            f"found {len(all_leaf_ids)}.",
        )

    if len(all_leaf_ids) != len(set(all_leaf_ids)):
        duplicates = sorted(
            {
                leaf_id
                for leaf_id in all_leaf_ids
                if all_leaf_ids.count(leaf_id) > 1
            }
        )

        fail(
            errors,
            "Duplicate query-topic IDs found: "
            + ", ".join(duplicates),
        )

    # ---------------------------------------------------------
    # Evidence notes
    # ---------------------------------------------------------

    evidence_notes = taxonomy.get("evidence_notes")

    if not isinstance(evidence_notes, dict):
        fail(errors, "evidence_notes must be a mapping.")
        evidence_notes = {}

    evidence_parent_ids = set(evidence_notes.keys())

    missing_evidence = EXPECTED_PARENTS - evidence_parent_ids
    unexpected_evidence = evidence_parent_ids - EXPECTED_PARENTS

    if missing_evidence:
        fail(
            errors,
            "Missing evidence_notes entries for: "
            + ", ".join(sorted(missing_evidence)),
        )

    if unexpected_evidence:
        fail(
            errors,
            "Unexpected evidence_notes entries for: "
            + ", ".join(sorted(unexpected_evidence)),
        )

    for parent_id, note in evidence_notes.items():
        location = f"evidence_notes.{parent_id}"

        if not isinstance(note, dict):
            fail(errors, f"{location} must be a mapping.")
            continue

        validate_non_empty_string(
            errors,
            note.get("evidence_status"),
            f"{location}.evidence_status",
        )

    # ---------------------------------------------------------
    # Design rules
    # ---------------------------------------------------------

    design_rules = taxonomy.get("design_rules")

    validate_non_empty_list(
        errors,
        design_rules,
        "design_rules",
    )

    # ---------------------------------------------------------
    # Freeze-state checks
    # ---------------------------------------------------------

    freeze_status = taxonomy.get("freeze_status")

    if not isinstance(freeze_status, dict):
        fail(errors, "freeze_status must be a mapping.")
        freeze_status = {}

    for key, expected_value in EXPECTED_FREEZE_STATUS.items():
        if key not in freeze_status:
            fail(errors, f"freeze_status missing key: {key}")
            continue

        actual_value = freeze_status[key]

        if actual_value is not expected_value:
            fail(
                errors,
                f"freeze_status.{key} must be {expected_value}, "
                f"found {actual_value!r}.",
            )

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    print("=" * 72)
    print("PASSPORT TAXONOMY STRUCTURAL VALIDATION")
    print("=" * 72)
    print(f"File: {TAXONOMY_PATH}")
    print(f"Version: {taxonomy.get('taxonomy_version')}")
    print(f"Service: {taxonomy.get('service_id')}")
    print(f"Status: {taxonomy.get('status')}")
    print(f"Parents: {len(parents)}")
    print(f"Total leaves: {len(all_leaf_ids)}")
    print()

    print("Leaf counts by parent:")

    for parent_id in EXPECTED_LEAF_COUNTS:
        print(
            f"  {parent_id}: "
            f"{leaf_count_by_parent.get(parent_id, 0)}"
        )

    print()

    if errors:
        print(f"RESULT: FAIL ({len(errors)} issue(s))")
        print()

        for index, error in enumerate(errors, start=1):
            print(f"{index}. {error}")

        sys.exit(1)

    print("RESULT: PASS")
    print("Passport taxonomy is structurally consistent.")
    print("Semantic audit and pilot review are recorded as passed.")
    print("The six-service shared label contract is frozen.")


if __name__ == "__main__":
    main()
