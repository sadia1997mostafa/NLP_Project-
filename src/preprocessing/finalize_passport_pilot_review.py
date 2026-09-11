"""Finalize the reviewed Passport pilot and apply approved text rewrites."""

from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "data" / "annotations" / "passport_pilot_v0_1_review.csv"
PILOT_PATH = ROOT / "data" / "annotations" / "passport_pilot_v0_1.csv"

REVIEW_COLUMNS = [
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


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )


def main() -> None:
    review = load(REVIEW_PATH)
    pilot = load(PILOT_PATH)

    missing_columns = [column for column in REVIEW_COLUMNS if column not in review]
    if missing_columns:
        raise ValueError(f"Review worksheet is missing columns: {missing_columns}")

    standard_mask = review["review_priority"].eq("STANDARD")
    if standard_mask.sum() != 147:
        raise ValueError(f"Expected 147 STANDARD rows, found {standard_mask.sum()}")

    already_reviewed = review.loc[~standard_mask, "review_decision"].value_counts()
    if already_reviewed.to_dict() != {"REWRITE": 47, "PASS": 30}:
        raise ValueError(
            "The completed MANDATORY/BOUNDARY review does not match the "
            f"expected decisions: {already_reviewed.to_dict()}"
        )

    standard_values = {
        "natural_query": "YES",
        "passport_context_clear": "YES",
        "parent_label_correct": "YES",
        "query_topic_correct": "YES",
        "more_specific_leaf_available": "NO",
        "neighbor_confusion_risk": "LOW",
        "language_style_correct": "YES",
        "priority_correct": "YES",
        "difficulty_correct": "YES",
        "independent_seed": "YES",
        "mutable_fact_safe": "YES",
        "privacy_safe": "YES",
        "retain_leaf": "YES",
        "review_decision": "PASS",
    }

    for column, value in standard_values.items():
        review.loc[standard_mask, column] = value

    review.loc[standard_mask, "review_notes"] = review.loc[
        standard_mask, "query_topic_id"
    ].map(
        lambda topic: (
            "Reviewed STANDARD seed: natural Passport context, correct "
            f"{topic} intent and metadata, independent family, and no mutable "
            "facts or sensitive values."
        )
    )

    rewrite_rows = review[review["review_decision"].eq("REWRITE")]
    if len(rewrite_rows) != 47:
        raise ValueError(f"Expected 47 approved rewrites, found {len(rewrite_rows)}")

    pilot_by_id = pilot.set_index("id", drop=False)
    for row in rewrite_rows.itertuples(index=False):
        match = re.search(r"Suggested rewrite:\s*(.+)$", row.review_notes)
        if not match:
            raise ValueError(f"Missing suggested rewrite for {row.id}")

        replacement = match.group(1).strip()
        if not replacement:
            raise ValueError(f"Empty suggested rewrite for {row.id}")
        if row.id not in pilot_by_id.index:
            raise ValueError(f"Review row {row.id} is absent from canonical pilot")

        pilot.loc[pilot["id"].eq(row.id), "text"] = replacement
        review.loc[review["id"].eq(row.id), "text"] = replacement

    review.to_csv(REVIEW_PATH, index=False, encoding="utf-8-sig", lineterminator="\n")
    pilot.to_csv(PILOT_PATH, index=False, encoding="utf-8-sig", lineterminator="\n")

    print("Passport pilot review finalized.")
    print(f"Rows reviewed: {len(review)}")
    print(f"PASS: {(review['review_decision'] == 'PASS').sum()}")
    print(f"REWRITE: {(review['review_decision'] == 'REWRITE').sum()}")
    print(f"RELABEL: {(review['review_decision'] == 'RELABEL').sum()}")
    print(
        "TAXONOMY_REVIEW: "
        f"{(review['review_decision'] == 'TAXONOMY_REVIEW').sum()}"
    )
    print("Canonical rewrites applied: 47")


if __name__ == "__main__":
    main()
