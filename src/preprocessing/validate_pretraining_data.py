"""Validate canonical data, OOD data and deterministic family-safe splits."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

import pandas as pd
import yaml

from service_pilot_framework import DATASET_COLUMNS
from text_normalization import normalized_key


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
SPLITS = ROOT / "data" / "splits"
SERVICES = ["NID", "BIRTH_REGISTRATION", "PASSPORT", "TAX", "POLICE_GD", "DRIVING_LICENCE"]
FILES = {
    "NID": "nid_canonical_v0_1.csv", "BIRTH_REGISTRATION": "birth_registration_canonical_v0_1.csv",
    "PASSPORT": "passport_canonical_v0_1.csv", "TAX": "tax_canonical_v0_1.csv",
    "POLICE_GD": "police_gd_canonical_v0_1.csv", "DRIVING_LICENCE": "driving_licence_canonical_v0_1.csv",
}
TAXONOMY_FILES = {
    "NID": "nid.yaml", "BIRTH_REGISTRATION": "birth_registration.yaml", "PASSPORT": "passport.yaml",
    "TAX": "tax.yaml", "POLICE_GD": "police_gd.yaml", "DRIVING_LICENCE": "driving_licence.yaml",
}


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def main() -> None:
    errors = []
    expected = {}
    for service, filename in TAXONOMY_FILES.items():
        data = yaml.safe_load((ROOT / "taxonomy" / filename).read_text(encoding="utf-8"))
        for parent_id, parent in data["parent_topics"].items():
            for leaf_id, leaf in parent["query_topics"].items():
                expected[leaf_id] = (service, parent_id, parent["display_name"], leaf["display_name"])

    frames = {}
    for service, filename in FILES.items():
        frame = read(PROCESSED / filename)
        frames[service] = frame
        if list(frame.columns) != DATASET_COLUMNS: errors.append(f"{service}: schema mismatch")
        if set(frame.service) != {service}: errors.append(f"{service}: wrong service value")
        counts = frame.groupby("query_topic_id").size()
        expected_leaves = {leaf for leaf, values in expected.items() if values[0] == service}
        if set(counts.index) != expected_leaves: errors.append(f"{service}: leaf coverage mismatch")
        if counts.min() < 12: errors.append(f"{service}: fewer than 12 rows in a leaf")
        for row in frame.itertuples(index=False):
            relation = expected.get(row.query_topic_id)
            if relation is None or (row.service, row.parent_topic_id, row.parent_topic, row.query_topic) != relation:
                errors.append(f"{row.id}: taxonomy relation mismatch")
        if frame.id.duplicated().any(): errors.append(f"{service}: duplicate IDs")
        if frame.parent_query_id.eq("").any(): errors.append(f"{service}: blank family")
        family_sizes = set(frame.groupby("parent_query_id").size())
        if family_sizes != {3}: errors.append(f"{service}: family sizes {family_sizes}")

    merged = read(PROCESSED / "all_services_canonical_v0_1.csv")
    if len(merged) != sum(map(len, frames.values())): errors.append("Merged row count mismatch")
    if merged.query_topic_id.nunique() != 264: errors.append("Merged intent count is not 264")
    duplicate_count = merged.text.map(normalized_key).duplicated().sum()
    if duplicate_count: errors.append(f"In-domain normalized duplicates: {duplicate_count}")

    ood = read(PROCESSED / "ood_canonical_v0_1.csv")
    if len(ood) != 360 or ood.query_topic_id.nunique() != 12: errors.append("OOD size/category mismatch")
    if set(ood.is_ood) != {"TRUE"} or set(ood.service) != {"OOD"}: errors.append("OOD labels invalid")
    if ood.text.map(normalized_key).duplicated().any(): errors.append("OOD normalized duplicates")
    if set(ood.text.map(normalized_key)) & set(merged.text.map(normalized_key)): errors.append("OOD/in-domain text overlap")

    splits = {name: read(SPLITS / f"{name}.csv") for name in ("train", "dev", "test")}
    family_sets = {name: set(frame.parent_query_id) for name, frame in splits.items()}
    text_sets = {name: set(frame.text.map(normalized_key)) for name, frame in splits.items()}
    family_leakage = sum(len(family_sets[a] & family_sets[b]) for a, b in (("train", "dev"), ("train", "test"), ("dev", "test")))
    text_leakage = sum(len(text_sets[a] & text_sets[b]) for a, b in (("train", "dev"), ("train", "test"), ("dev", "test")))
    if family_leakage: errors.append(f"Family leakage: {family_leakage}")
    if text_leakage: errors.append(f"Exact text split leakage: {text_leakage}")
    if sum(map(len, splits.values())) != len(merged): errors.append("Split row total mismatch")
    if set().union(*family_sets.values()) != set(merged.parent_query_id): errors.append("Split family coverage mismatch")

    print("=" * 72)
    print("SIX-SERVICE PRE-TRAINING DATA VALIDATION")
    print("=" * 72)
    for service, frame in frames.items():
        counts = frame.groupby("query_topic_id").size()
        print(f"{service}: rows={len(frame)} parents={frame.parent_topic_id.nunique()} leaves={frame.query_topic_id.nunique()} families={frame.parent_query_id.nunique()} min/max={counts.min()}/{counts.max()}")
    print("TOTAL IN-DOMAIN ROWS:", len(merged))
    print("TOTAL INTENTS:", merged.query_topic_id.nunique())
    print("OOD ROWS/CATEGORIES:", len(ood), "/", ood.query_topic_id.nunique())
    print("SPLIT ROWS:", {key: len(value) for key, value in splits.items()})
    print("SPLIT FAMILIES:", {key: value.parent_query_id.nunique() for key, value in splits.items()})
    print("FAMILY LEAKAGE:", family_leakage)
    print("EXACT TEXT SPLIT LEAKAGE:", text_leakage)
    print("IN-DOMAIN NORMALIZED DUPLICATES:", duplicate_count)
    if errors:
        print("RESULT: FAIL")
        for error in errors[:30]: print("ERROR:", error)
        sys.exit(1)
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
