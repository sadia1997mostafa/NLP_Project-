"""Targeted invariants for provisional Phase 1 paraphrase families."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from research.phase1.paraphrase_families.build_provisional_families import (
    EQUIVALENT,
    EXPECTED_PHASE0_MANIFEST_SHA256,
    HERE,
    ROOT,
    build_all,
)


PHASE0_MANIFEST = ROOT / "research/phase0/nid_5class_split_manifest_v1.csv"
TASK1_PAIRS = ROOT / "research/phase1/leakage_audit/near_duplicate_pairs_v1.csv"
PRIVATE_ROOT = ROOT.parent / f"{ROOT.name}_private" / "phase1"
PRIVATE_REVIEW = PRIVATE_ROOT / "near_duplicate_review_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_complete_family_map_and_safe_schema():
    manifest = read_csv(PHASE0_MANIFEST)
    families = read_csv(HERE / "provisional_paraphrase_family_map_v1.csv")
    decisions = read_csv(HERE / "provisional_pair_decisions_v1.csv")

    assert hashlib.sha256(PHASE0_MANIFEST.read_bytes()).hexdigest() == (
        EXPECTED_PHASE0_MANIFEST_SHA256
    )
    assert len(families) == len(manifest) == 1454
    assert len({row["sample_id"] for row in families}) == 1454
    assert {row["sample_id"] for row in families} == {
        row["sample_id"] for row in manifest
    }
    assert {row["adjudication_source"] for row in families} == {
        "codex_provisional"
    }

    forbidden = {"text", "text_a", "text_b", "query"}
    assert forbidden.isdisjoint(families[0])
    assert forbidden.isdisjoint(decisions[0])

    by_sample = {row["sample_id"]: row for row in families}
    family_counts: dict[str, int] = {}
    for row in families:
        family_counts[row["provisional_family_id"]] = (
            family_counts.get(row["provisional_family_id"], 0) + 1
        )
    assert all(
        int(row["family_size"]) == family_counts[row["provisional_family_id"]]
        for row in families
    )
    for row in decisions:
        if row["label_a"] != row["label_b"] and row["provisional_decision"] in EQUIVALENT:
            assert row["provisional_decision"] == "LABEL_CONFLICT_SAME_MEANING"
        if row["provisional_decision"] in EQUIVALENT:
            assert (
                by_sample[row["sample_id_a"]]["provisional_family_id"]
                == by_sample[row["sample_id_b"]]["provisional_family_id"]
            )


def test_private_boundaries_and_summary_contract():
    summary = json.loads(
        (HERE / "paraphrase_family_summary_v1.json").read_text(encoding="utf-8")
    )
    assert summary["source_row_count"] == 1454
    assert summary["candidate_pair_count"] == 99
    assert summary["adjudication_source"] == "codex_provisional"
    assert summary["final_human_adjudication_status"] == "PENDING"
    assert summary["labels_changed"] is False
    assert summary["phase0_split_changed"] is False
    assert summary["model_evaluations"] == 0

    for key in ("private_adjudicated_file", "private_human_review_queue"):
        private_path = Path(summary[key]["path"]).resolve()
        assert private_path.exists()
        assert not private_path.is_relative_to(ROOT.resolve())
        assert hashlib.sha256(private_path.read_bytes()).hexdigest() == summary[key][
            "sha256"
        ]


def test_family_mapping_is_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_private = tmp_path / "private-first"
    second_private = tmp_path / "private-second"

    arguments = (
        PHASE0_MANIFEST,
        HERE / "provisional_pair_decisions_v1.csv",
        TASK1_PAIRS,
        PRIVATE_REVIEW,
    )
    build_all(
        *arguments,
        first,
        first_private / "adjudicated.csv",
        first_private / "queue.csv",
    )
    build_all(
        *arguments,
        second,
        second_private / "adjudicated.csv",
        second_private / "queue.csv",
    )

    assert (
        first / "provisional_paraphrase_family_map_v1.csv"
    ).read_bytes() == (
        second / "provisional_paraphrase_family_map_v1.csv"
    ).read_bytes()
    assert (first / "human_review_queue_index_v1.csv").read_bytes() == (
        second / "human_review_queue_index_v1.csv"
    ).read_bytes()
