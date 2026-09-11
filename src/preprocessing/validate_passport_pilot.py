from pathlib import Path
import csv
import re
import sys
import unicodedata

import yaml


TAXONOMY_PATH = Path("taxonomy/passport.yaml")
DATASET_PATH = Path("data/annotations/passport_pilot_v0_1.csv")

EXPECTED_SERVICE = "PASSPORT"
EXPECTED_TAXONOMY_VERSION = "0.2.0"

EXPECTED_ROWS = 224
EXPECTED_PARENTS = 8
EXPECTED_TOPICS = 56
EXPECTED_FAMILIES = 224
ROWS_PER_TOPIC = 4

FIELDNAMES = [
    "id",
    "text",
    "service",
    "parent_topic_id",
    "parent_topic",
    "query_topic_id",
    "query_topic",
    "priority",
    "language_style",
    "privacy_present",
    "privacy_types",
    "source_type",
    "parent_query_id",
    "difficulty",
    "is_ood",
    "annotation_notes",
]

EXPECTED_PARENT_ROW_COUNTS = {
    "PASSPORT_APPLICATION": 28,
    "PASSPORT_DOCUMENTS": 32,
    "PASSPORT_ONLINE_ACCOUNT": 32,
    "PASSPORT_APPOINTMENT_AND_ENROLMENT": 28,
    "PASSPORT_REISSUE": 32,
    "PASSPORT_FEES_AND_PAYMENT": 32,
    "PASSPORT_STATUS_AND_DELIVERY": 28,
    "PASSPORT_GENERAL_INFORMATION": 12,
}

MEDIUM_PRIORITY_TOPICS = {
    "PASSPORT_DOCUMENTS_MISSING",
    "PASSPORT_ONLINE_ACCOUNT_ACTIVATION_EMAIL_NOT_RECEIVED",
    "PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM",
    "PASSPORT_APPOINTMENT_PROBLEM",
    "PASSPORT_REISSUE_WITH_INFORMATION_CHANGE",
    "PASSPORT_REISSUE_LOST",
    "PASSPORT_REISSUE_STOLEN",
    "PASSPORT_REISSUE_DAMAGED",
    "PASSPORT_PAYMENT_FAILURE",
    "PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED",
    "PASSPORT_PAYMENT_REFUND",
    "PASSPORT_APPLICATION_DELAY",
    "PASSPORT_DELIVERY_SLIP_LOST",
}

MANDATORY_REVIEW_TOPICS = {
    "PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC",
    "PASSPORT_DOCUMENTS_MISSING",
    "PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC",
    "PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM",
    "PASSPORT_APPOINTMENT_PROBLEM",
    "PASSPORT_APPLICATION_DELAY",
    "PASSPORT_GENERAL_SERVICE_GUIDANCE",
}

BASE_NOTE = (
    "Passport pilot v0.1 synthetic independent seed; "
    "human semantic review required before training."
)

EXPECTED_STYLE_BY_FAMILY = {
    1: "Formal",
    2: "Informal",
    3: "Mixed",
    4: "Mixed",
}

EXPECTED_DIFFICULTY_BY_FAMILY = {
    1: "Easy",
    2: "Medium",
    3: "Medium",
    4: "Hard",
}


def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def add_error(errors, message):
    errors.append(message)


def load_taxonomy(errors):
    if not TAXONOMY_PATH.exists():
        add_error(
            errors,
            f"Taxonomy file does not exist: {TAXONOMY_PATH}",
        )
        return None

    try:
        with TAXONOMY_PATH.open("r", encoding="utf-8") as file:
            taxonomy = yaml.safe_load(file)
    except Exception as exc:
        add_error(
            errors,
            f"Could not load taxonomy: {exc}",
        )
        return None

    if not isinstance(taxonomy, dict):
        add_error(errors, "Taxonomy root must be a mapping.")
        return None

    if taxonomy.get("service_id") != EXPECTED_SERVICE:
        add_error(
            errors,
            f"Expected taxonomy service_id={EXPECTED_SERVICE}, "
            f"found {taxonomy.get('service_id')!r}.",
        )

    if taxonomy.get("taxonomy_version") != EXPECTED_TAXONOMY_VERSION:
        add_error(
            errors,
            f"Expected taxonomy version "
            f"{EXPECTED_TAXONOMY_VERSION}, "
            f"found {taxonomy.get('taxonomy_version')!r}.",
        )

    if not taxonomy.get("freeze_status", {}).get(
        "semantic_audit_passed",
        False,
    ):
        add_error(
            errors,
            "Passport taxonomy semantic_audit_passed must be true.",
        )

    return taxonomy


def build_taxonomy_index(taxonomy, errors):
    leaf_index = {}

    if taxonomy is None:
        return leaf_index

    parents = taxonomy.get("parent_topics")

    if not isinstance(parents, dict):
        add_error(errors, "parent_topics must be a mapping.")
        return leaf_index

    if len(parents) != EXPECTED_PARENTS:
        add_error(
            errors,
            f"Expected {EXPECTED_PARENTS} taxonomy parents, "
            f"found {len(parents)}.",
        )

    for parent_id, parent_data in parents.items():
        if not isinstance(parent_data, dict):
            add_error(
                errors,
                f"Parent {parent_id} must be a mapping.",
            )
            continue

        parent_name = parent_data.get("display_name")
        query_topics = parent_data.get("query_topics")

        if not isinstance(query_topics, dict):
            add_error(
                errors,
                f"{parent_id}.query_topics must be a mapping.",
            )
            continue

        for topic_id, topic_data in query_topics.items():
            if topic_id in leaf_index:
                add_error(
                    errors,
                    f"Duplicate taxonomy query_topic_id: {topic_id}",
                )
                continue

            leaf_index[topic_id] = {
                "parent_topic_id": parent_id,
                "parent_topic": parent_name,
                "query_topic": topic_data.get("display_name"),
            }

    if len(leaf_index) != EXPECTED_TOPICS:
        add_error(
            errors,
            f"Expected {EXPECTED_TOPICS} taxonomy leaves, "
            f"found {len(leaf_index)}.",
        )

    return leaf_index


def load_dataset(errors):
    if not DATASET_PATH.exists():
        add_error(
            errors,
            f"Dataset file does not exist: {DATASET_PATH}",
        )
        return [], []

    try:
        with DATASET_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            header = reader.fieldnames or []
            rows = list(reader)

    except Exception as exc:
        add_error(
            errors,
            f"Could not read dataset: {exc}",
        )
        return [], []

    return header, rows


def validate_header(header, errors):
    if header != FIELDNAMES:
        add_error(
            errors,
            "Dataset header does not exactly match canonical schema.\n"
            f"Expected: {FIELDNAMES}\n"
            f"Found:    {header}",
        )


def parse_family_number(parent_query_id, topic_id):
    prefix = topic_id + "_F"

    if not parent_query_id.startswith(prefix):
        return None

    suffix = parent_query_id[len(prefix):]

    if not re.fullmatch(r"\d{2}", suffix):
        return None

    return int(suffix)


def expected_priority(topic_id):
    if topic_id in MEDIUM_PRIORITY_TOPICS:
        return "Medium"

    return "Low"


def expected_note(topic_id):
    note = BASE_NOTE

    if topic_id in MANDATORY_REVIEW_TOPICS:
        note += " Mandatory pilot-review leaf."

    return note


def validate_rows(rows, leaf_index, errors):
    if len(rows) != EXPECTED_ROWS:
        add_error(
            errors,
            f"Expected {EXPECTED_ROWS} rows, found {len(rows)}.",
        )

    row_ids = []
    family_ids = []
    exact_texts = []
    normalized_texts = []

    topic_counts = {}
    parent_counts = {}
    family_numbers_by_topic = {}

    source_type_counts = {}
    priority_counts = {}
    style_counts = {}
    difficulty_counts = {}

    for row_number, row in enumerate(rows, start=1):
        row_id = row.get("id", "")
        text = row.get("text", "")
        service = row.get("service", "")
        parent_topic_id = row.get("parent_topic_id", "")
        parent_topic = row.get("parent_topic", "")
        query_topic_id = row.get("query_topic_id", "")
        query_topic = row.get("query_topic", "")
        priority = row.get("priority", "")
        language_style = row.get("language_style", "")
        privacy_present = row.get("privacy_present", "")
        privacy_types = row.get("privacy_types", "")
        source_type = row.get("source_type", "")
        parent_query_id = row.get("parent_query_id", "")
        difficulty = row.get("difficulty", "")
        is_ood = row.get("is_ood", "")
        annotation_notes = row.get("annotation_notes", "")

        # -----------------------------------------------------
        # Sequential row ID
        # -----------------------------------------------------

        expected_row_id = f"PASSQ_{row_number:04d}"

        if row_id != expected_row_id:
            add_error(
                errors,
                f"Row {row_number}: expected id "
                f"{expected_row_id}, found {row_id!r}.",
            )

        row_ids.append(row_id)

        # -----------------------------------------------------
        # Text
        # -----------------------------------------------------

        if not text.strip():
            add_error(
                errors,
                f"{row_id or row_number}: text is empty.",
            )
        else:
            exact_texts.append(text)
            normalized_texts.append(normalize_text(text))

        # -----------------------------------------------------
        # Service
        # -----------------------------------------------------

        if service != EXPECTED_SERVICE:
            add_error(
                errors,
                f"{row_id}: service must be PASSPORT, "
                f"found {service!r}.",
            )

        # -----------------------------------------------------
        # Query topic and taxonomy relationship
        # -----------------------------------------------------

        if query_topic_id not in leaf_index:
            add_error(
                errors,
                f"{row_id}: unknown query_topic_id "
                f"{query_topic_id!r}.",
            )
        else:
            expected = leaf_index[query_topic_id]

            if parent_topic_id != expected["parent_topic_id"]:
                add_error(
                    errors,
                    f"{row_id}: incorrect parent_topic_id for "
                    f"{query_topic_id}. Expected "
                    f"{expected['parent_topic_id']}, "
                    f"found {parent_topic_id!r}.",
                )

            if parent_topic != expected["parent_topic"]:
                add_error(
                    errors,
                    f"{row_id}: incorrect parent_topic display name. "
                    f"Expected {expected['parent_topic']!r}, "
                    f"found {parent_topic!r}.",
                )

            if query_topic != expected["query_topic"]:
                add_error(
                    errors,
                    f"{row_id}: incorrect query_topic display name. "
                    f"Expected {expected['query_topic']!r}, "
                    f"found {query_topic!r}.",
                )

        topic_counts[query_topic_id] = (
            topic_counts.get(query_topic_id, 0) + 1
        )

        parent_counts[parent_topic_id] = (
            parent_counts.get(parent_topic_id, 0) + 1
        )

        # -----------------------------------------------------
        # Family
        # -----------------------------------------------------

        if not parent_query_id:
            add_error(
                errors,
                f"{row_id}: parent_query_id is empty.",
            )
        else:
            family_ids.append(parent_query_id)

            family_number = parse_family_number(
                parent_query_id,
                query_topic_id,
            )

            if family_number is None:
                add_error(
                    errors,
                    f"{row_id}: invalid parent_query_id "
                    f"{parent_query_id!r} for topic "
                    f"{query_topic_id}.",
                )
            else:
                family_numbers_by_topic.setdefault(
                    query_topic_id,
                    [],
                ).append(family_number)

                if family_number not in {1, 2, 3, 4}:
                    add_error(
                        errors,
                        f"{row_id}: family number must be 01-04, "
                        f"found F{family_number:02d}.",
                    )

                expected_style = EXPECTED_STYLE_BY_FAMILY.get(
                    family_number
                )

                if (
                    expected_style is not None
                    and language_style != expected_style
                ):
                    add_error(
                        errors,
                        f"{row_id}: family F{family_number:02d} "
                        f"must use language_style "
                        f"{expected_style}, found "
                        f"{language_style!r}.",
                    )

                expected_difficulty = (
                    EXPECTED_DIFFICULTY_BY_FAMILY.get(
                        family_number
                    )
                )

                if (
                    expected_difficulty is not None
                    and difficulty != expected_difficulty
                ):
                    add_error(
                        errors,
                        f"{row_id}: family F{family_number:02d} "
                        f"must use difficulty "
                        f"{expected_difficulty}, found "
                        f"{difficulty!r}.",
                    )

        # -----------------------------------------------------
        # Priority
        # -----------------------------------------------------

        expected_row_priority = expected_priority(query_topic_id)

        if priority != expected_row_priority:
            add_error(
                errors,
                f"{row_id}: expected priority "
                f"{expected_row_priority} for {query_topic_id}, "
                f"found {priority!r}.",
            )

        priority_counts[priority] = (
            priority_counts.get(priority, 0) + 1
        )

        # -----------------------------------------------------
        # Language style
        # -----------------------------------------------------

        if language_style not in {
            "Formal",
            "Informal",
            "Mixed",
        }:
            add_error(
                errors,
                f"{row_id}: invalid language_style "
                f"{language_style!r}.",
            )

        style_counts[language_style] = (
            style_counts.get(language_style, 0) + 1
        )

        # -----------------------------------------------------
        # Difficulty
        # -----------------------------------------------------

        if difficulty not in {
            "Easy",
            "Medium",
            "Hard",
        }:
            add_error(
                errors,
                f"{row_id}: invalid difficulty "
                f"{difficulty!r}.",
            )

        difficulty_counts[difficulty] = (
            difficulty_counts.get(difficulty, 0) + 1
        )

        # -----------------------------------------------------
        # Provenance
        # -----------------------------------------------------

        if source_type != "SYNTHETIC":
            add_error(
                errors,
                f"{row_id}: source_type must be SYNTHETIC, "
                f"found {source_type!r}.",
            )

        source_type_counts[source_type] = (
            source_type_counts.get(source_type, 0) + 1
        )

        # -----------------------------------------------------
        # Privacy and OOD
        # -----------------------------------------------------

        if privacy_present.upper() != "FALSE":
            add_error(
                errors,
                f"{row_id}: privacy_present must be FALSE, "
                f"found {privacy_present!r}.",
            )

        if privacy_types.strip():
            add_error(
                errors,
                f"{row_id}: privacy_types must be empty.",
            )

        if is_ood.upper() != "FALSE":
            add_error(
                errors,
                f"{row_id}: is_ood must be FALSE, "
                f"found {is_ood!r}.",
            )

        # -----------------------------------------------------
        # Annotation notes
        # -----------------------------------------------------

        expected_row_note = expected_note(query_topic_id)

        if annotation_notes != expected_row_note:
            add_error(
                errors,
                f"{row_id}: annotation_notes do not match "
                f"the pilot protocol.",
            )

    # ---------------------------------------------------------
    # Duplicate checks
    # ---------------------------------------------------------

    if len(row_ids) != len(set(row_ids)):
        add_error(errors, "Duplicate row IDs found.")

    if len(family_ids) != len(set(family_ids)):
        add_error(
            errors,
            "Duplicate parent_query_id values found. "
            "Pilot seeds must be independent families.",
        )

    if len(exact_texts) != len(set(exact_texts)):
        add_error(errors, "Exact duplicate query text found.")

    if len(normalized_texts) != len(set(normalized_texts)):
        add_error(errors, "Normalized duplicate query text found.")

    # ---------------------------------------------------------
    # Topic coverage
    # ---------------------------------------------------------

    if len(topic_counts) != EXPECTED_TOPICS:
        add_error(
            errors,
            f"Expected {EXPECTED_TOPICS} represented topics, "
            f"found {len(topic_counts)}.",
        )

    for topic_id in leaf_index:
        count = topic_counts.get(topic_id, 0)

        if count != ROWS_PER_TOPIC:
            add_error(
                errors,
                f"{topic_id}: expected {ROWS_PER_TOPIC} rows, "
                f"found {count}.",
            )

        family_numbers = sorted(
            family_numbers_by_topic.get(topic_id, [])
        )

        if family_numbers != [1, 2, 3, 4]:
            add_error(
                errors,
                f"{topic_id}: expected families "
                f"[1, 2, 3, 4], found {family_numbers}.",
            )

    # ---------------------------------------------------------
    # Parent coverage
    # ---------------------------------------------------------

    if len(parent_counts) != EXPECTED_PARENTS:
        add_error(
            errors,
            f"Expected {EXPECTED_PARENTS} represented parents, "
            f"found {len(parent_counts)}.",
        )

    for parent_id, expected_count in (
        EXPECTED_PARENT_ROW_COUNTS.items()
    ):
        actual_count = parent_counts.get(parent_id, 0)

        if actual_count != expected_count:
            add_error(
                errors,
                f"{parent_id}: expected {expected_count} rows, "
                f"found {actual_count}.",
            )

    # ---------------------------------------------------------
    # Family total
    # ---------------------------------------------------------

    if len(set(family_ids)) != EXPECTED_FAMILIES:
        add_error(
            errors,
            f"Expected {EXPECTED_FAMILIES} unique query families, "
            f"found {len(set(family_ids))}.",
        )

    return {
        "topic_counts": topic_counts,
        "parent_counts": parent_counts,
        "priority_counts": priority_counts,
        "style_counts": style_counts,
        "difficulty_counts": difficulty_counts,
        "source_type_counts": source_type_counts,
        "family_count": len(set(family_ids)),
    }


def print_summary(rows, stats, errors):
    print("=" * 72)
    print("PASSPORT PILOT DATASET VALIDATION")
    print("=" * 72)
    print(f"Dataset: {DATASET_PATH}")
    print(f"Taxonomy: {TAXONOMY_PATH}")
    print(f"Rows: {len(rows)}")
    print(f"Parents represented: {len(stats['parent_counts'])}")
    print(f"Query topics represented: {len(stats['topic_counts'])}")
    print(f"Unique query families: {stats['family_count']}")
    print()

    print("Rows by parent:")

    for parent_id in EXPECTED_PARENT_ROW_COUNTS:
        print(
            f"  {parent_id}: "
            f"{stats['parent_counts'].get(parent_id, 0)}"
        )

    print()

    print("Priority counts:")

    for value in ["Low", "Medium", "High"]:
        print(
            f"  {value}: "
            f"{stats['priority_counts'].get(value, 0)}"
        )

    print()

    print("Language-style counts:")

    for value in ["Formal", "Informal", "Mixed"]:
        print(
            f"  {value}: "
            f"{stats['style_counts'].get(value, 0)}"
        )

    print()

    print("Difficulty counts:")

    for value in ["Easy", "Medium", "Hard"]:
        print(
            f"  {value}: "
            f"{stats['difficulty_counts'].get(value, 0)}"
        )

    print()

    if errors:
        print(f"RESULT: FAIL ({len(errors)} issue(s))")
        print()

        for index, error in enumerate(errors, start=1):
            print(f"{index}. {error}")

        sys.exit(1)

    print("RESULT: PASS")
    print(
        "Passport pilot dataset is structurally consistent with "
        "taxonomy v0.2.0."
    )
    print(
        "All 224 rows are independent synthetic pilot seeds."
    )
    print(
        "DO NOT TRAIN: human semantic review is still required."
    )


def main():
    errors = []

    taxonomy = load_taxonomy(errors)

    leaf_index = build_taxonomy_index(
        taxonomy,
        errors,
    )

    header, rows = load_dataset(errors)

    validate_header(
        header,
        errors,
    )

    stats = validate_rows(
        rows,
        leaf_index,
        errors,
    )

    print_summary(
        rows,
        stats,
        errors,
    )


if __name__ == "__main__":
    main()