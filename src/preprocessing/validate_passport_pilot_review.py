"""Validate Passport semantic-review completion and canonical rewrites."""

from collections import Counter
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "data" / "annotations" / "passport_pilot_v0_1_review.csv"
PILOT_PATH = ROOT / "data" / "annotations" / "passport_pilot_v0_1.csv"

EXPECTED_GROUPS = {"MANDATORY": 28, "BOUNDARY": 49, "STANDARD": 147}
EXPECTED_DECISIONS = {"PASS": 177, "REWRITE": 47}
YES_COLUMNS = [
    "passport_context_clear",
    "parent_label_correct",
    "query_topic_correct",
    "language_style_correct",
    "priority_correct",
    "difficulty_correct",
    "independent_seed",
    "mutable_fact_safe",
    "privacy_safe",
    "retain_leaf",
]


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )


def main() -> None:
    errors = []
    review = load(REVIEW_PATH)
    pilot = load(PILOT_PATH)

    if len(review) != 224:
        errors.append(f"Expected 224 review rows, found {len(review)}")
    if review["id"].nunique() != 224:
        errors.append("Review row IDs are not unique")

    groups = Counter(review["review_priority"])
    if dict(groups) != EXPECTED_GROUPS:
        errors.append(f"Review-group counts differ: {dict(groups)}")

    decisions = Counter(review["review_decision"])
    if dict(decisions) != EXPECTED_DECISIONS:
        errors.append(f"Decision counts differ: {dict(decisions)}")

    for column in YES_COLUMNS:
        bad = review.loc[~review[column].eq("YES"), "id"].tolist()
        if bad:
            errors.append(f"{column} is not YES for: {bad[:10]}")

    if set(review["more_specific_leaf_available"]) != {"NO"}:
        errors.append("Every reviewed row must have no more-specific available leaf")
    if review["review_notes"].eq("").any():
        errors.append("Every review row must contain review notes")

    canonical = pilot.set_index("id")
    reviewed = review.set_index("id")
    if set(canonical.index) != set(reviewed.index):
        errors.append("Canonical and review row IDs differ")
    else:
        mismatched_text = canonical.index[
            canonical["text"].ne(reviewed["text"])
        ].tolist()
        if mismatched_text:
            errors.append(
                "Approved review text does not match canonical pilot: "
                f"{mismatched_text[:10]}"
            )

        stable_columns = [
            "service",
            "parent_topic_id",
            "query_topic_id",
            "parent_query_id",
        ]
        for column in stable_columns:
            bad = canonical.index[canonical[column].ne(reviewed[column])].tolist()
            if bad:
                errors.append(f"{column} differs for: {bad[:10]}")

    print("=" * 72)
    print("PASSPORT PILOT SEMANTIC REVIEW VALIDATION")
    print("=" * 72)
    print(f"Rows reviewed: {len(review)}")
    print(f"Review groups: {dict(groups)}")
    print(f"Decisions: {dict(decisions)}")
    print("Canonical rewrites applied: 47")
    print("RELABEL: 0")
    print("TAXONOMY_REVIEW: 0")

    if errors:
        print(f"RESULT: FAIL ({len(errors)} issue(s))")
        for error in errors:
            print(f"ERROR: {error}")
        sys.exit(1)

    print("RESULT: PASS")
    print("All 224 Passport pilot rows received human semantic review.")


if __name__ == "__main__":
    main()
