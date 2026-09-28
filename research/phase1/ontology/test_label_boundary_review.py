from __future__ import annotations

import csv
import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research" / "phase1" / "ontology"
EXPECTED_PAIRS = ("NID5-ND-000048", "NID5-ND-000050", "NID5-ND-000071")
EXPECTED_LABEL_HASH = "ce54be5d44b78b1d1233a438f051089c9c86fe41f47f50bd637f9b8d083216fc"
EXPECTED_FAMILY_HASH = "2e79a570eb6f9945c3bc69605b6762b4b27b838a8bf65f55af78f2bebfc6683c"


def load_tool():
    path = BASE / "review_label_boundaries.py"
    spec = importlib.util.spec_from_file_location("boundary_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return load_tool()


@pytest.fixture(scope="module")
def cases(tool):
    return tool.load_cases(ROOT, tool.default_queue_path(ROOT))


def test_exact_three_cases_and_six_samples(cases):
    assert len(cases) == 3
    assert tuple(case["pair_id"] for case in cases) == EXPECTED_PAIRS
    samples = {case[field] for case in cases for field in ("sample_id_a", "sample_id_b")}
    assert len(samples) == 6
    assert all(case["existing_family_equivalence"] == "EQUIVALENT" for case in cases)


def test_loading_cases_makes_no_automatic_decision(tool, tmp_path):
    output = tmp_path / "not_created.csv"
    assert not output.exists()
    loaded = tool.load_cases(ROOT, tool.default_queue_path(ROOT))
    assert not output.exists()
    assert all("canonical_boundary_decision" not in case for case in loaded)


def test_allowed_decisions_and_canonical_label_rules(tool, cases):
    case = cases[0]
    row_a = tool.build_resolved_row(case, "1", timestamp="2026-09-29T00:00:00+06:00")
    row_b = tool.build_resolved_row(case, "2", timestamp="2026-09-29T00:00:00+06:00")
    clarify = tool.build_resolved_row(case, "3", timestamp="2026-09-29T00:00:00+06:00")
    exclude = tool.build_resolved_row(case, "4", timestamp="2026-09-29T00:00:00+06:00")
    assert row_a["canonical_label_name"] == case["source_label_a"]
    assert row_b["canonical_label_name"] == case["source_label_b"]
    assert row_a["canonical_label_id"] == str(tool.LABEL_IDS[case["source_label_a"]])
    assert row_b["canonical_label_id"] == str(tool.LABEL_IDS[case["source_label_b"]])
    assert clarify["canonical_label_id"] == clarify["canonical_label_name"] == ""
    assert exclude["canonical_label_id"] == exclude["canonical_label_name"] == ""
    with pytest.raises(ValueError):
        tool.normalize_decision("AUTOMATIC_CHOICE")


def test_save_and_resume_without_overwriting_source(tool, cases, tmp_path):
    output = tmp_path / "private_resolved.csv"
    first = tool.build_resolved_row(cases[0], "1", "human test", "2026-09-29T00:00:00+06:00")
    tool.save_resolved(output, [first], cases)
    resumed = tool.read_resolved(output, cases)
    assert resumed == [first]
    second = tool.build_resolved_row(cases[1], "3", "", "2026-09-29T00:01:00+06:00")
    tool.save_resolved(output, resumed + [second], cases)
    assert [row["pair_id"] for row in tool.read_resolved(output, cases)] == list(EXPECTED_PAIRS[:2])
    modified = dict(first)
    modified["source_label_a"] = modified["source_label_b"]
    with pytest.raises(ValueError, match="Immutable source field changed"):
        tool.save_resolved(output, [modified], cases)


def test_private_output_is_outside_git(tool):
    output = tool.default_output_path(ROOT)
    assert not output.resolve().is_relative_to(ROOT.resolve())
    assert output.parent == ROOT.parent / f"{ROOT.name}_private" / "phase1"


def test_no_private_raw_text_is_embedded_in_git(cases):
    raw_values = {str(case[field]) for case in cases for field in ("text_a", "text_b")}
    for path in BASE.iterdir():
        if path.is_file():
            content = path.read_text(encoding="utf-8", errors="ignore")
            assert all(value not in content for value in raw_values)


def test_phase0_and_final_family_map_unchanged():
    labels = ROOT / "research" / "phase0" / "nid_5class_labels_v1.json"
    family = ROOT / "research" / "phase1" / "paraphrase_families" / "paraphrase_family_map_v1.csv"
    assert hashlib.sha256(labels.read_bytes()).hexdigest() == EXPECTED_LABEL_HASH
    assert hashlib.sha256(family.read_bytes()).hexdigest() == EXPECTED_FAMILY_HASH


def test_private_queue_source_labels_match_cases(tool, cases):
    with tool.default_queue_path(ROOT).open("r", encoding="utf-8-sig", newline="") as handle:
        queue = {row["sample_id"]: row for row in csv.DictReader(handle)}
    for case in cases:
        assert queue[case["sample_id_a"]]["source_label"] == case["source_label_a"]
        assert queue[case["sample_id_b"]]["source_label"] == case["source_label_b"]
