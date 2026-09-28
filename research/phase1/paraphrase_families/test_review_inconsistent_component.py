"""Tests for the component-level human grouping interface."""

from __future__ import annotations

import csv
import hashlib
import itertools

from research.phase1.paraphrase_families.review_inconsistent_component import (
    DEFAULT_COMPONENT_OUTPUT,
    DEFAULT_DECISIONS,
    DEFAULT_PAIR_OUTPUT,
    DEFAULT_RAW_PAIRS,
    EQUIVALENT,
    REQUIRED_PAIR_IDS,
    REQUIRED_SAMPLE_IDS,
    ROOT,
    derive_pair_relations,
    grouping_is_consistent,
    load_component,
    normalize_groups,
)


EXPECTED_PHASE0_MANIFEST_SHA256 = (
    "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
)


def loaded_component():
    return load_component(DEFAULT_RAW_PAIRS, DEFAULT_DECISIONS)


def grouping(pattern: str) -> dict[str, str]:
    return normalize_groups(dict(zip(REQUIRED_SAMPLE_IDS, pattern, strict=True)))


def equivalent_count(rows: list[dict[str, str]]) -> int:
    return sum(row["derived_equivalence_decision"] in EQUIVALENT for row in rows)


def test_exact_component_contract_and_private_paths():
    samples, pairs = loaded_component()
    assert [row["sample_id"] for row in samples] == list(REQUIRED_SAMPLE_IDS)
    assert len(pairs) == 6
    assert {row["pair_id"] for row in pairs} == set(REQUIRED_PAIR_IDS)
    assert len(
        {
            frozenset((row["sample_id_a"], row["sample_id_b"]))
            for row in pairs
        }
    ) == 6
    assert not DEFAULT_RAW_PAIRS.resolve().is_relative_to(ROOT.resolve())
    assert not DEFAULT_COMPONENT_OUTPUT.resolve().is_relative_to(ROOT.resolve())
    assert not DEFAULT_PAIR_OUTPUT.resolve().is_relative_to(ROOT.resolve())


def test_partition_edge_counts():
    samples, pairs = loaded_component()
    assert equivalent_count(
        derive_pair_relations(samples, pairs, grouping("AAAA"))
    ) == 6
    assert equivalent_count(
        derive_pair_relations(samples, pairs, grouping("ABCD"))
    ) == 0
    assert equivalent_count(
        derive_pair_relations(samples, pairs, grouping("AABB"))
    ) == 2


def test_cross_label_same_group_uses_label_conflict_decision():
    samples, pairs = loaded_component()
    by_id = {row["sample_id"]: row for row in samples}
    derived = derive_pair_relations(samples, pairs, grouping("AAAA"))
    cross_label = [
        row
        for row in derived
        if by_id[row["sample_id_a"]]["source_label"]
        != by_id[row["sample_id_b"]]["source_label"]
    ]
    assert cross_label
    assert all(
        row["derived_equivalence_decision"] == "LABEL_CONFLICT_SAME_MEANING"
        for row in cross_label
    )


def test_every_possible_partition_is_transitively_consistent():
    samples, pairs = loaded_component()
    for values in itertools.product("ABCD", repeat=4):
        groups = normalize_groups(
            dict(zip(REQUIRED_SAMPLE_IDS, values, strict=True))
        )
        derived = derive_pair_relations(samples, pairs, groups)
        assert grouping_is_consistent(groups, derived)


def test_git_safe_csvs_have_no_raw_text_and_phase0_is_unchanged():
    safe_csvs = (
        ROOT
        / "research/phase1/paraphrase_families/final_pair_decisions_v1.csv",
        ROOT
        / "research/phase1/paraphrase_families/human_pair_decisions_v1.csv",
    )
    forbidden = {"text", "text_a", "text_b", "query"}
    for path in safe_csvs:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            fields = set(csv.DictReader(handle).fieldnames or [])
        assert forbidden.isdisjoint(fields)
    phase0 = ROOT / "research/phase0/nid_5class_split_manifest_v1.csv"
    assert hashlib.sha256(phase0.read_bytes()).hexdigest() == (
        EXPECTED_PHASE0_MANIFEST_SHA256
    )
