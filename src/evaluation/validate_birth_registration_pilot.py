from collections import Counter, defaultdict
from pathlib import Path
import re
import sys

try:
    import pandas as pd
    import yaml
except ImportError as exc:
    print(f"ERROR: Missing dependency: {exc}")
    print("Run: python -m pip install pandas pyyaml")
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[2]

CSV_PATH = (
    ROOT
    / "data"
    / "annotations"
    / "birth_registration_pilot_v0_1.csv"
)

TAXONOMY_PATH = (
    ROOT
    / "taxonomy"
    / "birth_registration.yaml"
)


EXPECTED_COLUMNS = [
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


ALLOWED_PRIORITY = {
    "Low",
    "Medium",
    "High",
}

ALLOWED_LANGUAGE_STYLE = {
    "Formal",
    "Informal",
    "Mixed",
}

ALLOWED_SOURCE_TYPE = {
    "REAL",
    "SYNTHETIC",
    "PARAPHRASED",
}

ALLOWED_DIFFICULTY = {
    "Easy",
    "Medium",
    "Hard",
}

BOOLEAN_VALUES = {
    "true",
    "false",
}


def normalize_text(value):
    return " ".join(str(value).strip().lower().split())


def load_taxonomy():
    with TAXONOMY_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return yaml.safe_load(handle)


def fail_if_invalid_set(
    errors,
    df,
    column,
    allowed_values,
):
    values = set(
        df[column]
        .astype(str)
        .str.strip()
    )

    invalid = values - allowed_values

    if invalid:
        errors.append(
            f"{column} contains invalid values: "
            f"{sorted(invalid)}"
        )


def main():

    errors = []
    warnings = []

    if not CSV_PATH.exists():
        print(
            "ERROR: Dataset CSV not found:"
        )
        print(CSV_PATH)
        sys.exit(1)

    if not TAXONOMY_PATH.exists():
        print(
            "ERROR: Birth Registration taxonomy not found:"
        )
        print(TAXONOMY_PATH)
        sys.exit(1)

    taxonomy = load_taxonomy()

    if taxonomy.get("service_id") != "BIRTH_REGISTRATION":
        errors.append(
            "Taxonomy service_id must be "
            "BIRTH_REGISTRATION."
        )

    parents = taxonomy.get(
        "parent_topics",
        {},
    )

    expected_topics = {}

    for parent_id, parent in parents.items():

        parent_display_name = parent.get(
            "display_name"
        )

        query_topics = parent.get(
            "query_topics",
            {},
        )

        for query_id, query in query_topics.items():

            if query_id in expected_topics:
                errors.append(
                    f"Duplicate taxonomy query-topic ID: "
                    f"{query_id}"
                )

            expected_topics[query_id] = {
                "parent_id": parent_id,
                "parent_name": parent_display_name,
                "query_name": query.get(
                    "display_name"
                ),
            }

    df = pd.read_csv(
        CSV_PATH,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    actual_columns = list(df.columns)

    if actual_columns != EXPECTED_COLUMNS:
        errors.append(
            "CSV columns do not exactly match "
            "the canonical pilot schema.\n"
            f"Expected: {EXPECTED_COLUMNS}\n"
            f"Found:    {actual_columns}"
        )

    # Continue only when required columns exist.
    missing_columns = (
        set(EXPECTED_COLUMNS)
        - set(df.columns)
    )

    if missing_columns:
        print("=" * 72)
        print(
            "NAGORIKSHEBA AI — "
            "BIRTH REGISTRATION PILOT DATASET AUDIT"
        )
        print("=" * 72)

        for error in errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    # Strip surrounding whitespace from all columns.
    for column in EXPECTED_COLUMNS:
        df[column] = (
            df[column]
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------
    # Basic row checks
    # --------------------------------------------------

    if len(df) != 120:
        errors.append(
            f"Pilot v0.1 must contain exactly "
            f"120 rows, found {len(df)}."
        )

    empty_text = df["text"].eq("")

    if empty_text.any():
        errors.append(
            f"{int(empty_text.sum())} rows have "
            "empty text."
        )

    empty_ids = df["id"].eq("")

    if empty_ids.any():
        errors.append(
            f"{int(empty_ids.sum())} rows have "
            "empty IDs."
        )

    duplicate_ids = df[
        df["id"].duplicated(
            keep=False
        )
    ]

    if not duplicate_ids.empty:
        errors.append(
            "Duplicate row IDs found: "
            + ", ".join(
                sorted(
                    duplicate_ids["id"]
                    .unique()
                )
            )
        )

    invalid_row_ids = [
        row_id
        for row_id in df["id"]
        if not re.fullmatch(
            r"BRQ_\d{4}",
            row_id,
        )
    ]

    if invalid_row_ids:
        errors.append(
            "Invalid row ID format: "
            + ", ".join(
                invalid_row_ids[:10]
            )
        )

    normalized_text = df["text"].map(
        normalize_text
    )

    duplicate_text_mask = normalized_text.duplicated(
        keep=False
    )

    if duplicate_text_mask.any():
        duplicate_rows = df.loc[
            duplicate_text_mask,
            ["id", "text"],
        ]

        errors.append(
            f"{len(duplicate_rows)} rows participate "
            "in duplicate normalized query text."
        )

    # --------------------------------------------------
    # Service checks
    # --------------------------------------------------

    services = set(df["service"])

    if services != {
        "BIRTH_REGISTRATION"
    }:
        errors.append(
            "service column must contain only "
            f"BIRTH_REGISTRATION, found: "
            f"{sorted(services)}"
        )

    # --------------------------------------------------
    # Controlled vocabulary
    # --------------------------------------------------

    fail_if_invalid_set(
        errors,
        df,
        "priority",
        ALLOWED_PRIORITY,
    )

    fail_if_invalid_set(
        errors,
        df,
        "language_style",
        ALLOWED_LANGUAGE_STYLE,
    )

    fail_if_invalid_set(
        errors,
        df,
        "source_type",
        ALLOWED_SOURCE_TYPE,
    )

    fail_if_invalid_set(
        errors,
        df,
        "difficulty",
        ALLOWED_DIFFICULTY,
    )

    privacy_values = {
        value.lower()
        for value in df[
            "privacy_present"
        ]
    }

    invalid_privacy_values = (
        privacy_values
        - BOOLEAN_VALUES
    )

    if invalid_privacy_values:
        errors.append(
            "privacy_present contains invalid "
            f"values: "
            f"{sorted(invalid_privacy_values)}"
        )

    ood_values = {
        value.lower()
        for value in df[
            "is_ood"
        ]
    }

    invalid_ood_values = (
        ood_values
        - BOOLEAN_VALUES
    )

    if invalid_ood_values:
        errors.append(
            "is_ood contains invalid values: "
            f"{sorted(invalid_ood_values)}"
        )

    # --------------------------------------------------
    # Pilot v0.1 provenance expectations
    # --------------------------------------------------

    if set(df["source_type"]) != {
        "SYNTHETIC"
    }:
        errors.append(
            "Pilot v0.1 seed must currently contain "
            "only SYNTHETIC rows."
        )

    privacy_true_count = sum(
        value.lower() == "true"
        for value in df[
            "privacy_present"
        ]
    )

    if privacy_true_count != 0:
        errors.append(
            "Pilot v0.1 should currently contain "
            "0 privacy-positive rows because the "
            "privacy vocabulary is not frozen."
        )

    ood_true_count = sum(
        value.lower() == "true"
        for value in df[
            "is_ood"
        ]
    )

    if ood_true_count != 0:
        errors.append(
            "Pilot v0.1 should currently contain "
            "0 OOD rows. OOD examples will be "
            "added under the shared OOD contract."
        )

    unexpected_privacy_types = df.loc[
        df["privacy_present"]
        .str.lower()
        .eq("false")
        &
        df["privacy_types"]
        .ne(""),
        ["id", "privacy_types"],
    ]

    if not unexpected_privacy_types.empty:
        errors.append(
            "privacy_types must be empty when "
            "privacy_present is False."
        )

    # --------------------------------------------------
    # Taxonomy coverage
    # --------------------------------------------------

    actual_topics = set(
        df["query_topic_id"]
    )

    expected_topic_ids = set(
        expected_topics.keys()
    )

    missing_topics = (
        expected_topic_ids
        - actual_topics
    )

    unexpected_topics = (
        actual_topics
        - expected_topic_ids
    )

    if missing_topics:
        errors.append(
            "Taxonomy topics missing from pilot: "
            + ", ".join(
                sorted(missing_topics)
            )
        )

    if unexpected_topics:
        errors.append(
            "Unknown query-topic IDs in pilot: "
            + ", ".join(
                sorted(unexpected_topics)
            )
        )

    if len(expected_topic_ids) != 30:
        errors.append(
            f"Expected taxonomy to contain "
            f"30 query topics, found "
            f"{len(expected_topic_ids)}."
        )

    # --------------------------------------------------
    # Parent-child/name consistency
    # --------------------------------------------------

    relationship_errors = []

    for _, row in df.iterrows():

        query_id = row[
            "query_topic_id"
        ]

        if query_id not in expected_topics:
            continue

        expected = expected_topics[
            query_id
        ]

        if (
            row["parent_topic_id"]
            != expected["parent_id"]
        ):
            relationship_errors.append(
                f"{row['id']}: "
                f"{query_id} belongs under "
                f"{expected['parent_id']}, "
                f"found {row['parent_topic_id']}"
            )

        if (
            row["parent_topic"]
            != expected["parent_name"]
        ):
            relationship_errors.append(
                f"{row['id']}: parent_topic "
                "display name mismatch."
            )

        if (
            row["query_topic"]
            != expected["query_name"]
        ):
            relationship_errors.append(
                f"{row['id']}: query_topic "
                "display name mismatch."
            )

    if relationship_errors:
        errors.append(
            "Parent/child taxonomy mismatches:\n"
            + "\n".join(
                relationship_errors[:20]
            )
        )

    # --------------------------------------------------
    # Class balance
    # --------------------------------------------------

    topic_counts = Counter(
        df["query_topic_id"]
    )

    wrong_topic_counts = {
        topic_id: count
        for topic_id, count
        in topic_counts.items()
        if count != 4
    }

    if wrong_topic_counts:
        errors.append(
            "Every pilot leaf must have exactly "
            f"4 rows. Violations: "
            f"{wrong_topic_counts}"
        )

    # --------------------------------------------------
    # Query-family checks
    # --------------------------------------------------

    if df["parent_query_id"].eq("").any():
        errors.append(
            "Every row must have a "
            "parent_query_id."
        )

    family_topics = defaultdict(set)
    family_counts = Counter()

    for _, row in df.iterrows():

        family_id = row[
            "parent_query_id"
        ]

        query_id = row[
            "query_topic_id"
        ]

        family_topics[
            family_id
        ].add(query_id)

        family_counts[
            family_id
        ] += 1

        expected_prefix = (
            query_id + "_F"
        )

        if not family_id.startswith(
            expected_prefix
        ):
            errors.append(
                f"{row['id']}: parent_query_id "
                f"{family_id!r} does not match "
                f"query topic {query_id!r}."
            )

    cross_topic_families = {
        family_id: topics
        for family_id, topics
        in family_topics.items()
        if len(topics) != 1
    }

    if cross_topic_families:
        errors.append(
            "Query families span multiple "
            f"labels: {cross_topic_families}"
        )

    wrong_family_sizes = {
        family_id: count
        for family_id, count
        in family_counts.items()
        if count != 2
    }

    if wrong_family_sizes:
        errors.append(
            "Pilot v0.1 expects exactly 2 seed "
            "queries per family. Violations: "
            f"{wrong_family_sizes}"
        )

    if len(family_counts) != 60:
        errors.append(
            f"Expected 60 query families, "
            f"found {len(family_counts)}."
        )

    # --------------------------------------------------
    # Report
    # --------------------------------------------------

    parent_counts = Counter(
        df["parent_topic_id"]
    )

    print("=" * 72)
    print(
        "NAGORIKSHEBA AI — "
        "BIRTH REGISTRATION PILOT DATASET AUDIT"
    )
    print("=" * 72)

    print(f"Dataset: {CSV_PATH}")
    print(
        f"Taxonomy version: "
        f"{taxonomy.get('taxonomy_version')}"
    )
    print(f"Rows: {len(df)}")
    print(
        f"Unique row IDs: "
        f"{df['id'].nunique()}"
    )
    print(
        f"Unique query texts: "
        f"{normalized_text.nunique()}"
    )
    print(
        f"Parent topics: "
        f"{df['parent_topic_id'].nunique()}"
    )
    print(
        f"Query topics: "
        f"{df['query_topic_id'].nunique()}"
    )
    print(
        f"Query families: "
        f"{df['parent_query_id'].nunique()}"
    )

    print()
    print("ROWS PER PARENT")
    print("-" * 72)

    for parent_id in parents:
        print(
            f"{parent_id}: "
            f"{parent_counts.get(parent_id, 0)}"
        )

    print()
    print("ROWS PER QUERY TOPIC")
    print("-" * 72)

    for topic_id in expected_topics:
        print(
            f"{topic_id}: "
            f"{topic_counts.get(topic_id, 0)}"
        )

    print()
    print("PILOT PROVENANCE")
    print("-" * 72)
    print(
        "SYNTHETIC: "
        f"{sum(df['source_type'] == 'SYNTHETIC')}"
    )
    print(
        f"Privacy-positive rows: "
        f"{privacy_true_count}"
    )
    print(
        f"OOD rows: "
        f"{ood_true_count}"
    )

    print()
    print("FINAL RESULT")
    print("-" * 72)

    if warnings:
        for warning in warnings:
            print(f"WARNING: {warning}")

    if errors:
        print(
            "STATUS: PILOT DATASET VALIDATION FAILED"
        )
        print()

        for error in errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "STATUS: PILOT DATASET VALIDATION PASSED"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()