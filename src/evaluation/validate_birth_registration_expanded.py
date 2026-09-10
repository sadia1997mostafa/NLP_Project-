from collections import Counter, defaultdict
from pathlib import Path
import re
import sys

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]

CSV_PATH = (
    ROOT
    / "data"
    / "annotations"
    / "birth_registration_expanded_v0_2.csv"
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
    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


def load_taxonomy():
    with TAXONOMY_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return yaml.safe_load(handle)


def check_allowed(
    errors,
    df,
    column,
    allowed,
):
    values = set(
        df[column]
        .astype(str)
        .str.strip()
    )

    invalid = values - allowed

    if invalid:
        errors.append(
            f"{column} contains invalid values: "
            f"{sorted(invalid)}"
        )


def main():

    errors = []

    if not CSV_PATH.exists():
        print(
            f"ERROR: Dataset not found: "
            f"{CSV_PATH}"
        )
        sys.exit(1)

    if not TAXONOMY_PATH.exists():
        print(
            f"ERROR: Taxonomy not found: "
            f"{TAXONOMY_PATH}"
        )
        sys.exit(1)

    taxonomy = load_taxonomy()

    parents = taxonomy.get(
        "parent_topics",
        {},
    )

    expected_topics = {}

    for parent_id, parent in parents.items():

        for query_id, query in (
            parent
            .get(
                "query_topics",
                {},
            )
            .items()
        ):

            expected_topics[
                query_id
            ] = {
                "parent_id": parent_id,
                "parent_name": parent.get(
                    "display_name"
                ),
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

    # --------------------------------------------------
    # Schema
    # --------------------------------------------------

    if list(df.columns) != EXPECTED_COLUMNS:
        errors.append(
            "CSV columns do not exactly match "
            "the required schema."
        )

    missing_columns = (
        set(EXPECTED_COLUMNS)
        - set(df.columns)
    )

    if missing_columns:
        print(
            "ERROR: Missing columns:",
            sorted(missing_columns),
        )
        sys.exit(1)

    for column in EXPECTED_COLUMNS:
        df[column] = (
            df[column]
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------
    # Basic dataset size
    # --------------------------------------------------

    if len(df) != 360:
        errors.append(
            f"Expected 360 rows, found "
            f"{len(df)}."
        )

    if df["id"].nunique() != 360:
        errors.append(
            "Expected 360 unique row IDs."
        )

    if df["text"].eq("").any():
        errors.append(
            "Dataset contains empty query text."
        )

    normalized_text = df[
        "text"
    ].map(normalize_text)

    if normalized_text.nunique() != 360:
        errors.append(
            "Duplicate normalized query text "
            "was found."
        )

    # --------------------------------------------------
    # Row ID checks
    # --------------------------------------------------

    invalid_row_ids = []

    row_numbers = []

    for row_id in df["id"]:

        match = re.fullmatch(
            r"BRQ_(\d{4})",
            row_id,
        )

        if not match:
            invalid_row_ids.append(
                row_id
            )
            continue

        row_numbers.append(
            int(match.group(1))
        )

    if invalid_row_ids:
        errors.append(
            "Invalid row IDs: "
            + ", ".join(
                invalid_row_ids[:20]
            )
        )

    if (
        len(row_numbers) == 360
        and set(row_numbers)
        != set(range(1, 361))
    ):
        errors.append(
            "Row IDs must cover "
            "BRQ_0001 through BRQ_0360 "
            "exactly once."
        )

    # --------------------------------------------------
    # Service / controlled vocabulary
    # --------------------------------------------------

    if set(df["service"]) != {
        "BIRTH_REGISTRATION"
    }:
        errors.append(
            "service must contain only "
            "BIRTH_REGISTRATION."
        )

    check_allowed(
        errors,
        df,
        "priority",
        ALLOWED_PRIORITY,
    )

    check_allowed(
        errors,
        df,
        "language_style",
        ALLOWED_LANGUAGE_STYLE,
    )

    check_allowed(
        errors,
        df,
        "source_type",
        ALLOWED_SOURCE_TYPE,
    )

    check_allowed(
        errors,
        df,
        "difficulty",
        ALLOWED_DIFFICULTY,
    )

    privacy_values = {
        x.lower()
        for x in df[
            "privacy_present"
        ]
    }

    if not privacy_values.issubset(
        BOOLEAN_VALUES
    ):
        errors.append(
            "privacy_present contains "
            "invalid boolean values."
        )

    ood_values = {
        x.lower()
        for x in df[
            "is_ood"
        ]
    }

    if not ood_values.issubset(
        BOOLEAN_VALUES
    ):
        errors.append(
            "is_ood contains invalid "
            "boolean values."
        )

    # --------------------------------------------------
    # Privacy / OOD contract
    # --------------------------------------------------

    privacy_true = sum(
        x.lower() == "true"
        for x in df[
            "privacy_present"
        ]
    )

    ood_true = sum(
        x.lower() == "true"
        for x in df[
            "is_ood"
        ]
    )

    if privacy_true != 0:
        errors.append(
            "v0.2 must currently contain "
            "0 privacy-positive rows."
        )

    if ood_true != 0:
        errors.append(
            "v0.2 must currently contain "
            "0 OOD rows."
        )

    bad_privacy_types = df[
        df["privacy_present"]
        .str.lower()
        .eq("false")
        &
        df["privacy_types"]
        .ne("")
    ]

    if not bad_privacy_types.empty:
        errors.append(
            "privacy_types must be empty "
            "when privacy_present is False."
        )

    # --------------------------------------------------
    # Taxonomy coverage
    # --------------------------------------------------

    expected_topic_ids = set(
        expected_topics
    )

    actual_topic_ids = set(
        df["query_topic_id"]
    )

    if len(expected_topic_ids) != 30:
        errors.append(
            f"Taxonomy should contain "
            f"30 query topics, found "
            f"{len(expected_topic_ids)}."
        )

    missing_topics = (
        expected_topic_ids
        - actual_topic_ids
    )

    unknown_topics = (
        actual_topic_ids
        - expected_topic_ids
    )

    if missing_topics:
        errors.append(
            "Missing taxonomy topics: "
            + ", ".join(
                sorted(missing_topics)
            )
        )

    if unknown_topics:
        errors.append(
            "Unknown taxonomy topics: "
            + ", ".join(
                sorted(unknown_topics)
            )
        )

    # --------------------------------------------------
    # Taxonomy parent-child consistency
    # --------------------------------------------------

    relation_errors = []

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
            relation_errors.append(
                f"{row['id']}: wrong parent ID"
            )

        if (
            row["parent_topic"]
            != expected["parent_name"]
        ):
            relation_errors.append(
                f"{row['id']}: wrong parent name"
            )

        if (
            row["query_topic"]
            != expected["query_name"]
        ):
            relation_errors.append(
                f"{row['id']}: wrong query-topic name"
            )

    if relation_errors:
        errors.append(
            "Taxonomy relationship errors:\n"
            + "\n".join(
                relation_errors[:20]
            )
        )

    # --------------------------------------------------
    # Leaf balance
    # --------------------------------------------------

    topic_counts = Counter(
        df["query_topic_id"]
    )

    wrong_topic_counts = {
        topic: count
        for topic, count
        in topic_counts.items()
        if count != 12
    }

    if wrong_topic_counts:
        errors.append(
            "Every leaf must contain "
            "exactly 12 rows: "
            f"{wrong_topic_counts}"
        )

    # --------------------------------------------------
    # Family structure
    # --------------------------------------------------

    family_rows = defaultdict(list)

    for _, row in df.iterrows():

        family_id = row[
            "parent_query_id"
        ]

        if not re.fullmatch(
            r"BRP_\d{4}",
            family_id,
        ):
            errors.append(
                f"{row['id']}: invalid "
                f"parent_query_id "
                f"{family_id!r}"
            )

        family_rows[
            family_id
        ].append(row)

    expected_families = {
        f"BRP_{i:04d}"
        for i in range(
            1,
            121,
        )
    }

    actual_families = set(
        family_rows
    )

    if actual_families != expected_families:

        missing = (
            expected_families
            - actual_families
        )

        extra = (
            actual_families
            - expected_families
        )

        if missing:
            errors.append(
                "Missing families: "
                + ", ".join(
                    sorted(missing)
                )
            )

        if extra:
            errors.append(
                "Unexpected families: "
                + ", ".join(
                    sorted(extra)
                )
            )

    family_errors = []

    for family_id, members in (
        family_rows.items()
    ):

        if len(members) != 3:
            family_errors.append(
                f"{family_id}: "
                f"{len(members)} rows"
            )
            continue

        sources = Counter(
            row["source_type"]
            for row in members
        )

        if sources != {
            "SYNTHETIC": 1,
            "PARAPHRASED": 2,
        }:
            family_errors.append(
                f"{family_id}: "
                f"source distribution "
                f"{dict(sources)}"
            )

        labels = {
            row["query_topic_id"]
            for row in members
        }

        if len(labels) != 1:
            family_errors.append(
                f"{family_id}: "
                "members cross labels"
            )

        parents_used = {
            row["parent_topic_id"]
            for row in members
        }

        if len(parents_used) != 1:
            family_errors.append(
                f"{family_id}: "
                "members cross parents"
            )

        priorities = {
            row["priority"]
            for row in members
        }

        if len(priorities) != 1:
            family_errors.append(
                f"{family_id}: "
                "priority changed inside family"
            )

        privacy_states = {
            row["privacy_present"]
            .lower()
            for row in members
        }

        if len(privacy_states) != 1:
            family_errors.append(
                f"{family_id}: "
                "privacy state changed "
                "inside family"
            )

        ood_states = {
            row["is_ood"]
            .lower()
            for row in members
        }

        if len(ood_states) != 1:
            family_errors.append(
                f"{family_id}: "
                "OOD state changed "
                "inside family"
            )

        family_number = int(
            family_id.split("_")[1]
        )

        canonical_id = (
            f"BRQ_{family_number:04d}"
        )

        canonical = [
            row
            for row in members
            if row["id"]
            == canonical_id
        ]

        if len(canonical) != 1:
            family_errors.append(
                f"{family_id}: "
                f"missing canonical "
                f"{canonical_id}"
            )

        elif (
            canonical[0]["source_type"]
            != "SYNTHETIC"
        ):
            family_errors.append(
                f"{family_id}: "
                "canonical row must be "
                "SYNTHETIC"
            )

    if family_errors:
        errors.append(
            "Query-family errors:\n"
            + "\n".join(
                family_errors[:30]
            )
        )

    # --------------------------------------------------
    # Global provenance
    # --------------------------------------------------

    source_counts = Counter(
        df["source_type"]
    )

    expected_sources = {
        "SYNTHETIC": 120,
        "PARAPHRASED": 240,
    }

    if source_counts != expected_sources:
        errors.append(
            "Expected provenance "
            f"{expected_sources}, found "
            f"{dict(source_counts)}."
        )

    # --------------------------------------------------
    # Report
    # --------------------------------------------------

    print("=" * 72)

    print(
        "NAGORIKSHEBA AI — "
        "BIRTH REGISTRATION EXPANDED "
        "DATASET AUDIT"
    )

    print("=" * 72)

    print(
        f"Dataset: {CSV_PATH}"
    )

    print(
        f"Taxonomy version: "
        f"{taxonomy.get('taxonomy_version')}"
    )

    print(
        f"Rows: {len(df)}"
    )

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

    print("DATASET STRUCTURE")
    print("-" * 72)

    print(
        "Rows per query topic: "
        f"{sorted(set(topic_counts.values()))}"
    )

    family_sizes = Counter(
        len(members)
        for members
        in family_rows.values()
    )

    print(
        f"Family size distribution: "
        f"{dict(family_sizes)}"
    )

    print()

    print("PROVENANCE")
    print("-" * 72)

    print(
        f"SYNTHETIC: "
        f"{source_counts.get('SYNTHETIC', 0)}"
    )

    print(
        f"PARAPHRASED: "
        f"{source_counts.get('PARAPHRASED', 0)}"
    )

    print(
        f"Privacy-positive rows: "
        f"{privacy_true}"
    )

    print(
        f"OOD rows: "
        f"{ood_true}"
    )

    print()

    print("FINAL RESULT")
    print("-" * 72)

    if errors:

        print(
            "STATUS: EXPANDED DATASET "
            "VALIDATION FAILED"
        )

        print()

        for error in errors:
            print(
                f"ERROR: {error}"
            )

        sys.exit(1)

    print(
        "STATUS: EXPANDED DATASET "
        "VALIDATION PASSED"
    )

    sys.exit(0)


if __name__ == "__main__":
    main()
