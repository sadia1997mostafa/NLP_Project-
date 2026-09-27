"""Targeted tests for completed human-review consistency validation."""

from __future__ import annotations

import hashlib
import json

from research.phase1.paraphrase_families.validate_human_review import (
    DEFAULT_CORRECTION_QUEUE,
    DEFAULT_RESOLVED,
    EXPECTED_PHASE0_MANIFEST_SHA256,
    EXPECTED_RESOLVED_SHA256,
    ROOT,
    audit_consistency,
    validate_and_write,
    validate_resolved_review,
)
from research.phase1.paraphrase_families.review_human_queue import (
    ALLOWED_DECISIONS,
    DEFAULT_QUEUE,
    validate_queue,
)


def synthetic_row(
    *,
    text_a: str,
    text_b: str,
    label_a: str,
    label_b: str,
    decision: str,
    pair_id: str,
) -> dict[str, str]:
    return {
        "review_id": "SYNTHETIC-" + pair_id,
        "pair_id": pair_id,
        "sample_id_a": "SYNTHETIC-A-" + pair_id,
        "text_a": text_a,
        "label_a": label_a,
        "sample_id_b": "SYNTHETIC-B-" + pair_id,
        "text_b": text_b,
        "label_b": label_b,
        "human_decision": decision,
    }


def test_completed_review_integrity_and_hash_are_immutable():
    before = hashlib.sha256(DEFAULT_RESOLVED.read_bytes()).hexdigest()
    source = validate_queue(DEFAULT_QUEUE)
    resolved = validate_resolved_review(source, DEFAULT_RESOLVED)
    after = hashlib.sha256(DEFAULT_RESOLVED.read_bytes()).hexdigest()

    assert len(resolved) == 29
    assert before == after == EXPECTED_RESOLVED_SHA256
    assert all(row["human_decision"] in ALLOWED_DECISIONS for row in resolved)
    assert len({row["review_id"] for row in resolved}) == 29
    assert len({row["pair_id"] for row in resolved}) == 29


def test_hard_consistency_invariants_are_flagged():
    rows = [
        synthetic_row(
            text_a="same text",
            text_b="same   text",
            label_a="A",
            label_b="A",
            decision="RELATED_NOT_PARAPHRASE",
            pair_id="SAME-LABEL",
        ),
        synthetic_row(
            text_a="same text",
            text_b="same text",
            label_a="A",
            label_b="B",
            decision="NOT_PARAPHRASE",
            pair_id="CROSS-LABEL-EXACT",
        ),
        synthetic_row(
            text_a="first meaning",
            text_b="second wording",
            label_a="A",
            label_b="B",
            decision="SAME_MEANING",
            pair_id="CROSS-LABEL-ENCODING",
        ),
    ]
    summary, corrections = audit_consistency(rows)
    assert summary["mandatory_rereview_count"] == 3
    assert [row["violation_type"] for row in corrections] == [
        "EXACT_TEXT_SEMANTIC_CONTRADICTION",
        "EXACT_TEXT_LABEL_CONFLICT_CONTRADICTION",
        "CROSS_LABEL_EQUIVALENCE_ENCODING_CONTRADICTION",
    ]
    assert corrections[0]["suggested_valid_decision"] == "SAME_MEANING"
    assert all(
        row["suggested_valid_decision"] == "LABEL_CONFLICT_SAME_MEANING"
        for row in corrections[1:]
    )


def test_real_validation_is_deterministic_and_git_safe(tmp_path):
    summary_path = tmp_path / "summary.json"
    correction_path = tmp_path / "correction.csv"
    resolved_before = DEFAULT_RESOLVED.read_bytes()

    first = validate_and_write(
        DEFAULT_QUEUE,
        DEFAULT_RESOLVED,
        summary_path,
        correction_path,
    )
    first_summary_bytes = summary_path.read_bytes()
    first_correction_bytes = correction_path.read_bytes()
    second = validate_and_write(
        DEFAULT_QUEUE,
        DEFAULT_RESOLVED,
        summary_path,
        correction_path,
    )

    assert first == second
    assert summary_path.read_bytes() == first_summary_bytes
    assert correction_path.read_bytes() == first_correction_bytes
    assert DEFAULT_RESOLVED.read_bytes() == resolved_before
    assert not correction_path.resolve().is_relative_to(ROOT.resolve())
    assert first["mandatory_pair_ids"] == ["NID5-ND-000048"]
    assert first["status"] == "REQUIRES_HUMAN_CORRECTION"
    assert first["phase0_manifest_sha256"] == EXPECTED_PHASE0_MANIFEST_SHA256

    serialized = json.dumps(first)
    assert "text_a" not in serialized
    assert "text_b" not in serialized
    assert "Smart NID card" not in serialized


def test_default_correction_queue_is_private():
    assert not DEFAULT_CORRECTION_QUEUE.resolve().is_relative_to(ROOT.resolve())
