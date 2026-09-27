"""Non-semantic tests for the resumable human-review interface."""

from __future__ import annotations

import pytest

from research.phase1.paraphrase_families.review_human_queue import (
    DEFAULT_QUEUE,
    EXPECTED_ROWS,
    ROOT,
    load_progress,
    progress_counts,
    prompt_for_decision,
    validate_private_output_path,
    validate_queue,
)


def test_frozen_queue_loads_without_decisions(tmp_path):
    rows = validate_queue(DEFAULT_QUEUE)
    assert len(rows) == EXPECTED_ROWS
    assert all(not row["human_decision"] for row in rows)
    assert progress_counts(load_progress(rows, tmp_path / "missing_resolved.csv")) == (
        0,
        EXPECTED_ROWS,
    )


def test_cross_label_same_meaning_is_rejected(monkeypatch):
    answers = iter(["1", "4"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    synthetic = {"label_a": "LABEL_A", "label_b": "LABEL_B"}
    assert prompt_for_decision(synthetic) == "LABEL_CONFLICT_SAME_MEANING"


def test_resolved_output_must_be_outside_git(tmp_path):
    with pytest.raises(ValueError, match="outside the Git repository"):
        validate_private_output_path(ROOT / "forbidden.csv")
    validate_private_output_path(tmp_path / "allowed.csv")
