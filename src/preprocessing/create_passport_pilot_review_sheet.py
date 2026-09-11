from pathlib import Path
import csv


INPUT_PATH = Path("data/annotations/passport_pilot_v0_1.csv")
OUTPUT_PATH = Path(
    "data/annotations/passport_pilot_v0_1_review.csv"
)

MANDATORY_REVIEW_TOPICS = {
    "PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC",
    "PASSPORT_DOCUMENTS_MISSING",
    "PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC",
    "PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM",
    "PASSPORT_APPOINTMENT_PROBLEM",
    "PASSPORT_APPLICATION_DELAY",
    "PASSPORT_GENERAL_SERVICE_GUIDANCE",
}

REVIEW_COLUMNS = [
    "review_priority",
    "natural_query",
    "passport_context_clear",
    "parent_label_correct",
    "query_topic_correct",
    "more_specific_leaf_available",
    "neighbor_confusion_risk",
    "language_style_correct",
    "priority_correct",
    "difficulty_correct",
    "independent_seed",
    "mutable_fact_safe",
    "privacy_safe",
    "retain_leaf",
    "review_decision",
    "review_notes",
]

ALLOWED_REVIEW_DECISIONS = (
    "PASS / REWRITE / RELABEL / TAXONOMY_REVIEW"
)


def load_rows():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Pilot dataset not found: {INPUT_PATH}"
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        original_fields = reader.fieldnames or []
        rows = list(reader)

    if not rows:
        raise ValueError("Passport pilot dataset is empty.")

    return original_fields, rows


def review_priority(row):
    if row["query_topic_id"] in MANDATORY_REVIEW_TOPICS:
        return "MANDATORY"

    if row["difficulty"] == "Hard":
        return "BOUNDARY"

    return "STANDARD"


def build_review_rows(rows):
    review_rows = []

    for row in rows:
        output = dict(row)

        output.update(
            {
                "review_priority": review_priority(row),
                "natural_query": "",
                "passport_context_clear": "",
                "parent_label_correct": "",
                "query_topic_correct": "",
                "more_specific_leaf_available": "",
                "neighbor_confusion_risk": "",
                "language_style_correct": "",
                "priority_correct": "",
                "difficulty_correct": "",
                "independent_seed": "",
                "mutable_fact_safe": "",
                "privacy_safe": "",
                "retain_leaf": "",
                "review_decision": "",
                "review_notes": "",
            }
        )

        review_rows.append(output)

    return review_rows


def write_review_sheet(original_fields, rows):
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = original_fields + REVIEW_COLUMNS

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows):
    priority_counts = {
        "MANDATORY": 0,
        "BOUNDARY": 0,
        "STANDARD": 0,
    }

    mandatory_topics_seen = set()

    for row in rows:
        level = row["review_priority"]

        priority_counts[level] = (
            priority_counts.get(level, 0) + 1
        )

        if level == "MANDATORY":
            mandatory_topics_seen.add(
                row["query_topic_id"]
            )

    print("=" * 72)
    print("PASSPORT PILOT HUMAN-REVIEW WORKSHEET")
    print("=" * 72)

    print(f"Input: {INPUT_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Rows: {len(rows)}")
    print()

    print("Review-priority counts:")
    print(
        f"  MANDATORY: "
        f"{priority_counts['MANDATORY']}"
    )
    print(
        f"  BOUNDARY: "
        f"{priority_counts['BOUNDARY']}"
    )
    print(
        f"  STANDARD: "
        f"{priority_counts['STANDARD']}"
    )

    print()

    print(
        "Mandatory review topics represented: "
        f"{len(mandatory_topics_seen)}"
    )

    for topic_id in sorted(mandatory_topics_seen):
        print(f"  {topic_id}")

    print()
    print("RESULT: PASS")
    print("Human-review worksheet created.")
    print()
    print(
        "Allowed review_decision values:"
    )
    print(
        f"  {ALLOWED_REVIEW_DECISIONS}"
    )
    print()
    print(
        "Do not train or expand the Passport dataset "
        "until human semantic review is complete."
    )


def main():
    original_fields, source_rows = load_rows()

    review_rows = build_review_rows(
        source_rows
    )

    write_review_sheet(
        original_fields,
        review_rows,
    )

    print_summary(review_rows)


if __name__ == "__main__":
    main()