"""Targeted invariants for the Phase 1 lexical leakage audit."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from research.phase1.leakage_audit.run_leakage_audit import (
    DEFAULT_PRIVATE_REVIEW,
    DEFAULT_SOURCE,
    EXPECTED_LABELS,
    EXPECTED_SPLITS,
    HERE,
    ROOT,
    load_inputs,
    run_audit,
)


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_frozen_inputs_and_candidate_invariants():
    records = load_inputs(
        DEFAULT_SOURCE,
        ROOT / "research/phase0/nid_5class_split_manifest_v1.csv",
    )
    assert len(records) == 1454
    assert {row["label"] for row in records} == EXPECTED_LABELS
    assert {row["split"] for row in records} == set(EXPECTED_SPLITS)

    pairs = read_csv(HERE / "near_duplicate_pairs_v1.csv")
    assert pairs
    assert len({row["pair_id"] for row in pairs}) == len(pairs)
    assert all(row["sample_id_a"] != row["sample_id_b"] for row in pairs)
    unordered = {
        frozenset((row["sample_id_a"], row["sample_id_b"])) for row in pairs
    }
    assert len(unordered) == len(pairs)
    for row in pairs:
        for field in ("char_tfidf_cosine", "token_jaccard", "sequence_similarity"):
            assert 0.0 <= float(row[field]) <= 1.0
        assert row["split_a"] in EXPECTED_SPLITS
        assert row["split_b"] in EXPECTED_SPLITS
        assert row["label_a"] in EXPECTED_LABELS
        assert row["label_b"] in EXPECTED_LABELS
    assert "text" not in pairs[0]
    assert "text_a" not in pairs[0]
    assert "text_b" not in pairs[0]


def test_exact_duplicates_and_private_review_contract():
    manifest = json.loads(
        (HERE / "leakage_audit_manifest_v1.json").read_text(encoding="utf-8")
    )
    exact = manifest["exact_duplicates"]["phase0_normalized"]
    assert exact["groups"] == 7
    assert exact["rows_in_groups"] == 14
    assert exact["cross_label_groups"] == 2
    assert exact["cross_split_groups"] == 0
    private = Path(manifest["private_review"]["path"]).resolve()
    assert private == DEFAULT_PRIVATE_REVIEW.resolve()
    assert not private.is_relative_to(ROOT.resolve())
    assert private.exists()
    assert hashlib.sha256(private.read_bytes()).hexdigest() == manifest["private_review"]["sha256"]


def test_git_safe_outputs_are_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    arguments = (
        DEFAULT_SOURCE,
        ROOT / "research/phase0/nid_5class_split_manifest_v1.csv",
        HERE / "audit_normalization_v1.yaml",
    )
    run_audit(*arguments, first, None)
    run_audit(*arguments, second, None)
    expected = {
        "near_duplicate_pairs_v1.csv",
        "leakage_threshold_summary_v1.csv",
        "split_similarity_summary_v1.json",
        "label_conflict_summary_v1.json",
        "template_candidate_summary_v1.json",
        "leakage_audit_manifest_v1.json",
    }
    assert {path.name for path in first.iterdir()} == expected
    assert {path.name for path in second.iterdir()} == expected
    for name in expected:
        assert (first / name).read_bytes() == (second / name).read_bytes()
