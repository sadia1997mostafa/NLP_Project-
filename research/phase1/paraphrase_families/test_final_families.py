"""Integrity and determinism tests for the final paraphrase-family freeze."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from research.phase1.paraphrase_families.build_final_families import (
    EXPECTED_PHASE0_MANIFEST_SHA256,
    FAMILY_MAP,
    FINAL_DECISIONS,
    HUMAN_CONSISTENCY,
    HUMAN_DECISIONS,
    PHASE0_MANIFEST,
    ROOT,
    build_final,
)


HERE = Path(__file__).resolve().parent
PRIVATE_ROOT = ROOT.parent / f"{ROOT.name}_private" / "phase1"
EXPECTED_FAMILY_MAP_SHA256 = (
    "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c"
)
EXPECTED_COMPONENT = {
    "NID5-ND-000056": "EQUIVALENT",
    "NID5-ND-000057": "NOT_EQUIVALENT",
    "NID5-ND-000058": "NOT_EQUIVALENT",
    "NID5-ND-000067": "NOT_EQUIVALENT",
    "NID5-ND-000068": "NOT_EQUIVALENT",
    "NID5-ND-000071": "EQUIVALENT",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_final_decision_counts_correction_and_component_override():
    decisions = read_csv(FINAL_DECISIONS)
    human = read_csv(HUMAN_DECISIONS)
    assert len(decisions) == 99
    assert len(human) == 29
    assert Counter(row["semantic_decision_source"] for row in decisions) == {
        "human_confirmed": 29,
        "codex_provisional": 70,
    }
    by_pair = {row["pair_id"]: row for row in decisions}
    assert by_pair["NID5-ND-000048"]["semantic_decision"] == (
        "LABEL_CONFLICT_SAME_MEANING"
    )
    assert by_pair["NID5-ND-000048"]["semantic_decision_source"] == (
        "human_confirmed"
    )
    for pair_id, expected in EXPECTED_COMPONENT.items():
        assert by_pair[pair_id]["family_equivalence"] == expected
        assert by_pair[pair_id]["family_equivalence_source"] == (
            "human_component_review"
        )
    assert by_pair["NID5-ND-000057"]["semantic_decision"] == "SAME_MEANING"
    assert by_pair["NID5-ND-000067"]["semantic_decision"] == "SAME_MEANING"
    assert by_pair["NID5-ND-000057"]["semantic_decision_source"] == (
        "codex_provisional"
    )


def test_all_samples_assigned_once_with_unchanged_labels_and_sizes():
    phase0 = read_csv(PHASE0_MANIFEST)
    families = read_csv(FAMILY_MAP)
    assert len(phase0) == len(families) == 1454
    assert len({row["sample_id"] for row in families}) == 1454
    phase0_by_id = {row["sample_id"]: row for row in phase0}
    assert set(phase0_by_id) == {row["sample_id"] for row in families}

    counts = Counter(row["paraphrase_family_id"] for row in families)
    for row in families:
        assert row["label_id"] == phase0_by_id[row["sample_id"]]["label_id"]
        assert row["label_name"] == phase0_by_id[row["sample_id"]]["label_name"]
        assert int(row["family_size"]) == counts[row["paraphrase_family_id"]]
        assert re.fullmatch(
            r"NID5-PF-FINAL-\d{4}",
            row["paraphrase_family_id"],
        )


def test_component_is_exactly_two_two_sample_families():
    families = {
        row["sample_id"]: row for row in read_csv(FAMILY_MAP)
    }
    first = {"NID5-V1-000769", "NID5-V1-000826"}
    second = {"NID5-V1-000894", "NID5-V1-001449"}
    first_ids = {families[sample]["paraphrase_family_id"] for sample in first}
    second_ids = {families[sample]["paraphrase_family_id"] for sample in second}
    assert len(first_ids) == len(second_ids) == 1
    assert first_ids != second_ids
    assert all(int(families[sample]["family_size"]) == 2 for sample in first | second)


def test_equivalence_graph_has_no_authoritative_contradiction():
    families = {
        row["sample_id"]: row["paraphrase_family_id"]
        for row in read_csv(FAMILY_MAP)
    }
    for row in read_csv(FINAL_DECISIONS):
        same_family = families[row["sample_id_a"]] == families[row["sample_id_b"]]
        if row["family_equivalence"] == "EQUIVALENT":
            assert same_family
        if same_family:
            assert row["family_equivalence"] != "NOT_EQUIVALENT"


def test_map_is_deterministic_and_matches_frozen_hash(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for target in (first, second):
        build_final(
            PHASE0_MANIFEST,
            FINAL_DECISIONS,
            HUMAN_DECISIONS,
            HUMAN_CONSISTENCY,
            target / "map.csv",
            target / "summary.json",
            target / "manifest.json",
        )
    assert (first / "map.csv").read_bytes() == (second / "map.csv").read_bytes()
    assert hashlib.sha256((first / "map.csv").read_bytes()).hexdigest() == (
        EXPECTED_FAMILY_MAP_SHA256
    )
    assert hashlib.sha256(FAMILY_MAP.read_bytes()).hexdigest() == (
        EXPECTED_FAMILY_MAP_SHA256
    )


def test_git_safe_outputs_and_private_boundaries():
    safe_csvs = (
        HUMAN_DECISIONS,
        FINAL_DECISIONS,
        FAMILY_MAP,
    )
    forbidden = {"text", "text_a", "text_b", "query"}
    for path in safe_csvs:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            fields = set(csv.DictReader(handle).fieldnames or [])
        assert forbidden.isdisjoint(fields)

    private_files = (
        PRIVATE_ROOT / "human_review_queue_v1_final.csv",
        PRIVATE_ROOT / "human_review_correction_queue_v1.csv",
        PRIVATE_ROOT / "component_review_0001_v1.csv",
        PRIVATE_ROOT / "component_review_0001_pairs_v1.csv",
    )
    assert all(path.exists() for path in private_files)
    assert all(not path.resolve().is_relative_to(ROOT.resolve()) for path in private_files)
    assert hashlib.sha256(PHASE0_MANIFEST.read_bytes()).hexdigest() == (
        EXPECTED_PHASE0_MANIFEST_SHA256
    )

    summary = json.loads(
        (HERE / "paraphrase_family_final_summary_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["unresolved_mandatory_reviews"] == 0
    assert summary["transitive_consistency"] == "PASS"
    assert summary["fully_human_annotated"] is False
