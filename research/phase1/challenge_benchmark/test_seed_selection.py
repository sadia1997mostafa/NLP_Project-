"""Targeted tests for deterministic Phase 1 challenge seed selection."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import review_challenge_seeds as review_tool  # noqa: E402
import select_challenge_seed_candidates as selector  # noqa: E402
import validate_seed_candidates as validator  # noqa: E402


PRIVATE_ROOT = ROOT.parent / f"{ROOT.name}_private"
SOURCE = PRIVATE_ROOT / "phase0" / "nid_5class_source_v1.csv"
SPLIT = ROOT / "research" / "phase0" / "nid_5class_split_manifest_v1.csv"
FAMILY = ROOT / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv"
CONFLICTS = ROOT / "research" / "phase1" / "ontology" / "nid_5class_source_conflicts_v1.csv"
ONTOLOGY = ROOT / "research" / "phase1" / "ontology" / "nid_5class_ontology_manifest_v1.json"
PROTOCOL = HERE / "challenge_protocol_manifest_v1.json"
PRIVATE_REVIEW = PRIVATE_ROOT / "phase1" / "challenge_seed_review_queue_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_frozen_dependencies_and_eligible_counts() -> None:
    assert selector.sha256(SOURCE) == selector.EXPECTED_SOURCE_HASH
    assert selector.sha256(SPLIT) == selector.EXPECTED_SPLIT_HASH
    assert selector.sha256(FAMILY) == selector.EXPECTED_FAMILY_HASH
    assert selector.sha256(ONTOLOGY) == selector.EXPECTED_ONTOLOGY_MANIFEST_HASH
    assert selector.sha256(PROTOCOL) == selector.EXPECTED_PROTOCOL_MANIFEST_HASH
    units, _ = selector.reconstruct_eligible_units(SOURCE, SPLIT, FAMILY, CONFLICTS, ONTOLOGY, PROTOCOL)
    assert Counter(int(row["label_id"]) for row in units) == Counter(selector.EXPECTED_ELIGIBLE_FAMILIES)
    assert len(units) == 209


def test_committed_candidate_invariants() -> None:
    candidates = read_csv(HERE / "challenge_seed_candidates_v1.csv")
    reserves = read_csv(HERE / "challenge_seed_reserve_order_v1.csv")
    assert len(candidates) == 100
    assert len(reserves) == 109
    assert Counter(int(row["label_id"]) for row in candidates) == Counter({i: 20 for i in range(5)})
    assert len({row["sample_id"] for row in candidates}) == 100
    assert len({row["paraphrase_family_id"] for row in candidates}) == 100
    assert not ({row["sample_id"] for row in candidates} & {row["sample_id"] for row in reserves})
    assert not ({row["paraphrase_family_id"] for row in candidates} & {row["paraphrase_family_id"] for row in reserves})
    assert all(row["stable_selection_hash"] == selector.stable_key(row["sample_id"]) for row in candidates + reserves)


def test_full_validator() -> None:
    result = validator.validate(
        SOURCE, SPLIT, FAMILY, CONFLICTS, ONTOLOGY, PROTOCOL,
        HERE / "challenge_seed_candidates_v1.csv",
        HERE / "challenge_seed_reserve_order_v1.csv",
        HERE / "challenge_seed_candidate_profile_v1.json",
        HERE / "challenge_seed_selection_manifest_v1.json",
        PRIVATE_REVIEW,
    )
    assert result == {"candidates": 100, "reserve": 109, "eligible_units": 209}


def test_deterministic_rerun_is_byte_identical(tmp_path: Path) -> None:
    output = tmp_path / "out"
    private = tmp_path / "private" / "challenge_seed_review_queue_v1.csv"
    selector.generate(SOURCE, SPLIT, FAMILY, CONFLICTS, ONTOLOGY, PROTOCOL, output, private)
    for name in (
        "challenge_seed_candidates_v1.csv",
        "challenge_seed_reserve_order_v1.csv",
        "challenge_seed_candidate_profile_v1.json",
        "challenge_seed_selection_manifest_v1.json",
    ):
        assert (output / name).read_bytes() == (HERE / name).read_bytes()
    assert private.read_bytes() == PRIVATE_REVIEW.read_bytes()


def test_no_training_dev_or_conflict_leakage() -> None:
    candidates = read_csv(HERE / "challenge_seed_candidates_v1.csv")
    family_rows = read_csv(FAMILY)
    splits: dict[str, set[str]] = {}
    for row in family_rows:
        splits.setdefault(row["paraphrase_family_id"], set()).add(row["phase0_split"])
    conflict_ids = {
        sample_id for row in read_csv(CONFLICTS)
        for sample_id in (row["sample_id_a"], row["sample_id_b"])
    }
    assert all(row["phase0_split"] == "test" for row in candidates)
    assert all("train" not in splits[row["paraphrase_family_id"]] for row in candidates)
    assert all("dev" not in splits[row["paraphrase_family_id"]] for row in candidates)
    assert not ({row["sample_id"] for row in candidates} & conflict_ids)


def test_private_queue_mirrors_candidates_and_is_undecided() -> None:
    candidates = read_csv(HERE / "challenge_seed_candidates_v1.csv")
    review = read_csv(PRIVATE_REVIEW)
    assert len(review) == 100
    assert [row["sample_id"] for row in review] == [row["sample_id"] for row in candidates]
    assert all(
        not row[field]
        for row in review
        for field in ("classifiable", "explicit_enough", "transformable", "review_decision", "human_notes")
    )
    assert PRIVATE_REVIEW.resolve().is_relative_to(ROOT.parent.resolve())
    assert not PRIVATE_REVIEW.resolve().is_relative_to(ROOT.resolve())


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (("YES", "YES", "YES"), "ACCEPT"),
        (("NO", "YES", "YES"), "REJECT"),
        (("YES", "NO", "YES"), "REJECT"),
        (("YES", "YES", "NO"), "REJECT"),
    ],
)
def test_review_decision_contract(values: tuple[str, str, str], expected: str) -> None:
    assert review_tool.derive_decision(*values) == expected


def test_review_decision_rejects_incomplete_checks() -> None:
    with pytest.raises(ValueError):
        review_tool.derive_decision("YES", "", "YES")


def test_review_resume_preserves_completed_decisions(tmp_path: Path) -> None:
    queue_copy = tmp_path / "queue.csv"
    queue_copy.write_bytes(PRIVATE_REVIEW.read_bytes())
    rows = review_tool.load_review_state(queue_copy, tmp_path / "resolved.csv")
    rows[0].update(
        classifiable="YES", explicit_enough="YES", transformable="YES",
        review_decision="ACCEPT", human_notes="", reviewer="human",
        review_timestamp="2026-09-29T00:00:00+00:00",
    )
    resolved = tmp_path / "resolved.csv"
    review_tool.write_resolved(resolved, rows)
    resumed = review_tool.load_review_state(queue_copy, resolved)
    assert resumed[0]["review_decision"] == "ACCEPT"
    assert resumed[1]["review_decision"] == ""


def test_git_safe_outputs_have_no_raw_text_fields() -> None:
    banned = {"text", "text_a", "text_b", "query", "raw_text"}
    for name in ("challenge_seed_candidates_v1.csv", "challenge_seed_reserve_order_v1.csv"):
        with (HERE / name).open("r", encoding="utf-8-sig", newline="") as handle:
            assert not (set(next(csv.reader(handle))) & banned)
    profile = json.loads((HERE / "challenge_seed_candidate_profile_v1.json").read_text(encoding="utf-8"))
    manifest = json.loads((HERE / "challenge_seed_selection_manifest_v1.json").read_text(encoding="utf-8"))
    assert profile["raw_text_emitted"] is False
    assert manifest["raw_text_in_git_artifacts"] is False


def test_no_final_panel_or_challenge_generation() -> None:
    assert not (HERE / "challenge_seed_panel_v1.csv").exists()
    profile = json.loads((HERE / "challenge_seed_candidate_profile_v1.json").read_text(encoding="utf-8"))
    manifest = json.loads((HERE / "challenge_seed_selection_manifest_v1.json").read_text(encoding="utf-8"))
    assert profile["final_seed_panel_frozen"] is False
    assert manifest["human_review_status"] == "PENDING"
    assert manifest["final_seed_status"] == "NOT_FROZEN"
