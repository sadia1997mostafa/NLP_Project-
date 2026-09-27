"""Run the deterministic Phase 1 lexical leakage audit without model evaluation."""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import platform
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import sklearn
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = (
    ROOT.parent / f"{ROOT.name}_private" / "phase0" / "nid_5class_source_v1.csv"
)
DEFAULT_PRIVATE_REVIEW = (
    ROOT.parent
    / f"{ROOT.name}_private"
    / "phase1"
    / "near_duplicate_review_v1.csv"
)
EXPECTED_SOURCE_SHA256 = (
    "6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa"
)
EXPECTED_SPLIT_SHA256 = (
    "4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1"
)
EXPECTED_SPLITS = {"train": 1017, "dev": 219, "test": 218}
EXPECTED_LABELS = {
    "NID Information Correction",
    "New NID Registration",
    "Lost/Stolen NID",
    "NID Online Problem",
    "Smart ID Card",
}
PAIR_COLUMNS = [
    "pair_id",
    "sample_id_a",
    "sample_id_b",
    "split_a",
    "split_b",
    "label_a",
    "label_b",
    "same_label",
    "same_split",
    "char_tfidf_cosine",
    "token_jaccard",
    "sequence_similarity",
    "normalized_hash_equality",
    "audit_normalized_hash_equality",
]
PRIVATE_COLUMNS = [
    "pair_id",
    "sample_id_a",
    "text_a",
    "label_a",
    "split_a",
    "sample_id_b",
    "text_b",
    "label_b",
    "split_b",
    "char_tfidf_cosine",
    "token_jaccard",
    "sequence_similarity",
    "review_priority",
    "review_decision",
    "review_notes",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def frozen_normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def audit_normalize(value: object) -> str:
    primary = frozen_normalize(value)
    lowered = []
    for character in primary:
        name = unicodedata.name(character, "")
        lowered.append(character.lower() if "LATIN" in name else character)
    return " ".join("".join(lowered).split())


def punctuation_light(value: object) -> str:
    primary = audit_normalize(value)
    replaced = "".join(
        " " if unicodedata.category(character).startswith("P") else character
        for character in primary
    )
    return " ".join(replaced.split())


def token_jaccard(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    union = left_tokens | right_tokens
    if not union:
        return 1.0
    return len(left_tokens & right_tokens) / len(union)


def load_inputs(source: Path, manifest_path: Path) -> list[dict[str, Any]]:
    require(sha256_file(source) == EXPECTED_SOURCE_SHA256, "Frozen source hash mismatch")
    require(
        sha256_file(manifest_path) == EXPECTED_SPLIT_SHA256,
        "Frozen Phase 0 split manifest hash mismatch",
    )
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        source_rows = list(reader)
    require(len(source_rows) == 1454, f"Expected 1454 source rows; found {len(source_rows)}")
    require("text" in header and "problem" in header, "Source schema changed")
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    require(len(manifest) == 1454, "Phase 0 manifest row count changed")
    require(
        Counter(row["split"] for row in manifest) == Counter(EXPECTED_SPLITS),
        "Phase 0 split counts changed",
    )
    require(len({row["sample_id"] for row in manifest}) == 1454, "Sample IDs not unique")
    text_index = header.index("text")
    label_index = header.index("problem")
    records = []
    for row in manifest:
        source_index = int(row["source_row_number"]) - 1
        require(0 <= source_index < 1454, "Source row number outside frozen range")
        cells = source_rows[source_index]
        text = cells[text_index]
        label = cells[label_index]
        require(label == row["label_name"], f"Label mismatch: {row['sample_id']}")
        frozen = frozen_normalize(text)
        require(
            sha256_text(frozen) == row["normalized_text_sha256"],
            f"Frozen normalized hash mismatch: {row['sample_id']}",
        )
        primary = audit_normalize(text)
        light = punctuation_light(text)
        records.append(
            {
                "sample_id": row["sample_id"],
                "text": text,
                "label": label,
                "split": row["split"],
                "frozen_hash": row["normalized_text_sha256"],
                "audit_hash": sha256_text(primary),
                "punctuation_light_hash": sha256_text(light),
                "comparison_text": light,
            }
        )
    require({row["label"] for row in records} == EXPECTED_LABELS, "Label set changed")
    return records


def duplicate_stats(records: list[dict[str, Any]], hash_field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record[hash_field]].append(record)
    duplicates = [members for members in groups.values() if len(members) > 1]
    cross_label = [members for members in duplicates if len({x["label"] for x in members}) > 1]
    cross_split = [members for members in duplicates if len({x["split"] for x in members}) > 1]
    return {
        "groups": len(duplicates),
        "rows_in_groups": sum(len(members) for members in duplicates),
        "same_label_groups": sum(len({x["label"] for x in members}) == 1 for members in duplicates),
        "cross_label_groups": len(cross_label),
        "cross_label_pairs": sum(
            1
            for members in cross_label
            for i, left in enumerate(members)
            for right in members[i + 1 :]
            if left["label"] != right["label"]
        ),
        "cross_split_groups": len(cross_split),
    }


def split_pair_name(left: str, right: str) -> str:
    pair = frozenset((left, right))
    if pair == {"train", "dev"}:
        return "train_dev"
    if pair == {"train", "test"}:
        return "train_test"
    if pair == {"dev", "test"}:
        return "dev_test"
    return "same_split"


def build_pairs(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], np.ndarray]:
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        lowercase=False,
        sublinear_tf=True,
        norm="l2",
    )
    matrix = vectorizer.fit_transform([row["comparison_text"] for row in records])
    similarity = np.clip((matrix @ matrix.T).toarray(), 0.0, 1.0)
    np.fill_diagonal(similarity, -1.0)
    candidate_indexes = np.argwhere(np.triu(similarity, k=1) >= 0.80)
    pairs = []
    for counter, (left_index, right_index) in enumerate(candidate_indexes, start=1):
        left = records[int(left_index)]
        right = records[int(right_index)]
        left_text = left["comparison_text"]
        right_text = right["comparison_text"]
        cosine = float(similarity[left_index, right_index])
        pairs.append(
            {
                "pair_id": f"NID5-ND-{counter:06d}",
                "sample_id_a": left["sample_id"],
                "sample_id_b": right["sample_id"],
                "split_a": left["split"],
                "split_b": right["split"],
                "label_a": left["label"],
                "label_b": right["label"],
                "same_label": left["label"] == right["label"],
                "same_split": left["split"] == right["split"],
                "char_tfidf_cosine": cosine,
                "token_jaccard": token_jaccard(left_text, right_text),
                "sequence_similarity": difflib.SequenceMatcher(
                    None, left_text, right_text, autojunk=False
                ).ratio(),
                "normalized_hash_equality": left["frozen_hash"] == right["frozen_hash"],
                "audit_normalized_hash_equality": left["audit_hash"] == right["audit_hash"],
                "punctuation_light_hash_equality": (
                    left["punctuation_light_hash"] == right["punctuation_light_hash"]
                ),
                "left_index": int(left_index),
                "right_index": int(right_index),
                "split_pair": split_pair_name(left["split"], right["split"]),
            }
        )
    return pairs, similarity


def pair_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_pairs": len(rows),
        "same_split_pairs": sum(row["same_split"] for row in rows),
        "cross_split_pairs": sum(not row["same_split"] for row in rows),
        "same_label_pairs": sum(row["same_label"] for row in rows),
        "cross_label_pairs": sum(not row["same_label"] for row in rows),
        "same_label_cross_split_pairs": sum(
            row["same_label"] and not row["same_split"] for row in rows
        ),
        "cross_label_cross_split_pairs": sum(
            not row["same_label"] and not row["same_split"] for row in rows
        ),
        "train_dev_pairs": sum(row["split_pair"] == "train_dev" for row in rows),
        "train_test_pairs": sum(row["split_pair"] == "train_test" for row in rows),
        "dev_test_pairs": sum(row["split_pair"] == "dev_test" for row in rows),
    }


def build_threshold_rows(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    definitions = [
        ("band", "gte_0.95", 0.95, None),
        ("band", "0.90_to_0.95", 0.90, 0.95),
        ("band", "0.85_to_0.90", 0.85, 0.90),
        ("band", "0.80_to_0.85", 0.80, 0.85),
        ("threshold", "gte_0.95", 0.95, None),
        ("threshold", "gte_0.90", 0.90, None),
        ("threshold", "gte_0.85", 0.85, None),
        ("threshold", "gte_0.80", 0.80, None),
    ]
    output = []
    for summary_type, label, lower, upper in definitions:
        if summary_type == "band" and upper is not None:
            selected = [x for x in pairs if lower <= x["char_tfidf_cosine"] < upper]
        else:
            selected = [x for x in pairs if x["char_tfidf_cosine"] >= lower]
        output.append(
            {
                "summary_type": summary_type,
                "label": label,
                "lower_inclusive": lower,
                "upper_exclusive": "" if upper is None else upper,
                **pair_summary(selected),
            }
        )
    return output


def distribution(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p90": float(np.quantile(values, 0.90)),
        "p95": float(np.quantile(values, 0.95)),
        "maximum": float(np.max(values)),
    }


def build_similarity_summary(records: list[dict[str, Any]], similarity: np.ndarray) -> dict[str, Any]:
    train_indexes = np.array([i for i, row in enumerate(records) if row["split"] == "train"])
    heldout = {}
    for split in ("dev", "test"):
        indexes = np.array([i for i, row in enumerate(records) if row["split"] == split])
        maxima = similarity[np.ix_(indexes, train_indexes)].max(axis=1)
        heldout[f"{split}_maximum_similarity_to_train"] = distribution(maxima)
    strongest = []
    for index, record in enumerate(records):
        neighbor_index = int(np.argmax(similarity[index]))
        neighbor = records[neighbor_index]
        strongest.append(
            {
                "sample_id": record["sample_id"],
                "neighbor_sample_id": neighbor["sample_id"],
                "char_tfidf_cosine": float(similarity[index, neighbor_index]),
                "same_label": record["label"] == neighbor["label"],
                "same_split": record["split"] == neighbor["split"],
            }
        )
    all_values = np.array([row["char_tfidf_cosine"] for row in strongest])
    return {
        **heldout,
        "all_rows_strongest_neighbor_distribution": distribution(all_values),
        "all_rows_strongest_neighbor_threshold_counts": {
            "gte_0.95": int(np.sum(all_values >= 0.95)),
            "gte_0.90": int(np.sum(all_values >= 0.90)),
            "gte_0.85": int(np.sum(all_values >= 0.85)),
            "gte_0.80": int(np.sum(all_values >= 0.80)),
        },
        "strongest_neighbors": strongest,
    }


def common_prefix_length(left: str, right: str) -> int:
    count = 0
    for a, b in zip(left, right):
        if a != b:
            break
        count += 1
    return count


def common_suffix_length(left: str, right: str) -> int:
    return common_prefix_length(left[::-1], right[::-1])


def template_summary(records: list[dict[str, Any]], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    parents = list(range(len(records)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parents[root_right] = root_left

    counts = Counter()
    template_pairs = []
    for pair in pairs:
        left = records[pair["left_index"]]["comparison_text"]
        right = records[pair["right_index"]]["comparison_text"]
        shorter = max(1, min(len(left), len(right)))
        long_prefix = common_prefix_length(left, right) >= max(20, int(0.60 * shorter))
        long_suffix = common_suffix_length(left, right) >= max(20, int(0.60 * shorter))
        left_tokens, right_tokens = left.split(), right.split()
        few_substitutions = (
            len(left_tokens) == len(right_tokens)
            and sum(a != b for a, b in zip(left_tokens, right_tokens)) <= 2
        )
        near_frame = pair["sequence_similarity"] >= 0.90 and (
            long_prefix or long_suffix or few_substitutions
        )
        counts["long_prefix_pairs"] += long_prefix
        counts["long_suffix_pairs"] += long_suffix
        counts["few_token_substitution_pairs"] += few_substitutions
        counts["near_identical_frame_pairs"] += near_frame
        if near_frame:
            template_pairs.append(pair)
            union(pair["left_index"], pair["right_index"])
    groups: dict[int, list[int]] = defaultdict(list)
    involved = {p["left_index"] for p in template_pairs} | {
        p["right_index"] for p in template_pairs
    }
    for index in involved:
        groups[find(index)].append(index)
    components = list(groups.values())
    return {
        **dict(counts),
        "candidate_family_groups": len(components),
        "rows_in_candidate_families": sum(len(group) for group in components),
        "largest_candidate_family": max((len(group) for group in components), default=0),
        "cross_split_candidate_families": sum(
            len({records[index]["split"] for index in group}) > 1 for group in components
        ),
        "cross_label_candidate_families": sum(
            len({records[index]["label"] for index in group}) > 1 for group in components
        ),
        "interpretation": (
            "Computational template-like lexical family candidates only; "
            "manual review is required before declaring paraphrase families."
        ),
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_audit(
    source: Path,
    phase0_manifest: Path,
    normalization_config: Path,
    output_dir: Path,
    private_review: Path | None,
) -> dict[str, Any]:
    config = yaml.safe_load(normalization_config.read_text(encoding="utf-8"))
    require(config["protocol"] == "AUDIT-NORM-V1", "Audit normalization protocol changed")
    records = load_inputs(source, phase0_manifest)
    frozen_duplicates = duplicate_stats(records, "frozen_hash")
    audit_duplicates = duplicate_stats(records, "audit_hash")
    punctuation_duplicates = duplicate_stats(records, "punctuation_light_hash")
    pairs, similarity = build_pairs(records)
    threshold_rows = build_threshold_rows(pairs)
    similarity_summary = build_similarity_summary(records, similarity)
    conflict_summary = {
        "frozen_exact": frozen_duplicates,
        "audit_normalized_exact": audit_duplicates,
        "punctuation_light_exact": punctuation_duplicates,
        "cross_label_candidate_pairs": {
            f"gte_{threshold:.2f}": sum(
                (not pair["same_label"])
                and pair["char_tfidf_cosine"] >= threshold
                for pair in pairs
            )
            for threshold in (0.95, 0.90, 0.85, 0.80)
        },
        "labels_changed": False,
    }
    templates = template_summary(records, pairs)

    output_dir.mkdir(parents=True, exist_ok=True)
    public_pairs = [{key: row[key] for key in PAIR_COLUMNS} for row in pairs]
    write_csv(output_dir / "near_duplicate_pairs_v1.csv", public_pairs, PAIR_COLUMNS)
    threshold_fields = list(threshold_rows[0])
    write_csv(
        output_dir / "leakage_threshold_summary_v1.csv",
        threshold_rows,
        threshold_fields,
    )
    write_json(output_dir / "split_similarity_summary_v1.json", similarity_summary)
    write_json(output_dir / "label_conflict_summary_v1.json", conflict_summary)
    write_json(output_dir / "template_candidate_summary_v1.json", templates)

    private_metadata = None
    if private_review is not None:
        resolved_private = private_review.resolve()
        require(
            not resolved_private.is_relative_to(ROOT.resolve()),
            "Private review output must be outside the Git repository",
        )
        private_review.parent.mkdir(parents=True, exist_ok=True)
        review_rows = []
        for pair in pairs:
            left, right = records[pair["left_index"]], records[pair["right_index"]]
            if (not pair["same_split"] and pair["char_tfidf_cosine"] >= 0.95) or (
                not pair["same_label"] and pair["char_tfidf_cosine"] >= 0.90
            ):
                priority = "HIGH"
            elif not pair["same_split"] and pair["char_tfidf_cosine"] >= 0.90:
                priority = "MEDIUM"
            else:
                priority = "LOW"
            review_rows.append(
                {
                    "pair_id": pair["pair_id"],
                    "sample_id_a": left["sample_id"],
                    "text_a": left["text"],
                    "label_a": left["label"],
                    "split_a": left["split"],
                    "sample_id_b": right["sample_id"],
                    "text_b": right["text"],
                    "label_b": right["label"],
                    "split_b": right["split"],
                    "char_tfidf_cosine": pair["char_tfidf_cosine"],
                    "token_jaccard": pair["token_jaccard"],
                    "sequence_similarity": pair["sequence_similarity"],
                    "review_priority": priority,
                    "review_decision": "",
                    "review_notes": "",
                }
            )
        write_csv(private_review, review_rows, PRIVATE_COLUMNS)
        private_metadata = {
            "path": str(resolved_private),
            "rows": len(review_rows),
            "sha256": sha256_file(private_review),
            "size_bytes": private_review.stat().st_size,
            "inside_git_repository": False,
        }

    output_files = [
        "near_duplicate_pairs_v1.csv",
        "leakage_threshold_summary_v1.csv",
        "split_similarity_summary_v1.json",
        "label_conflict_summary_v1.json",
        "template_candidate_summary_v1.json",
    ]
    manifest = {
        "audit_id": "NID5-PHASE1-LEAKAGE-AUDIT-V1",
        "audit_normalization": "AUDIT-NORM-V1",
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "phase0_split_manifest_sha256": EXPECTED_SPLIT_SHA256,
        "normalization_config_sha256": sha256_file(normalization_config),
        "rows": len(records),
        "labels": sorted(EXPECTED_LABELS),
        "candidate_minimum_cosine": 0.80,
        "candidate_pairs": len(pairs),
        "exact_duplicates": {
            "phase0_normalized": frozen_duplicates,
            "audit_normalized": audit_duplicates,
            "punctuation_light": punctuation_duplicates,
        },
        "git_safe_outputs": {
            name: {
                "size_bytes": (output_dir / name).stat().st_size,
                "sha256": sha256_file(output_dir / name),
                "contains_raw_text": False,
            }
            for name in output_files
        },
        "private_review": private_metadata,
        "package_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "phase0_test_evaluations_before": 1,
        "test_model_evaluations_during_audit": 0,
        "phase0_test_evaluations_after": 1,
    }
    write_json(output_dir / "leakage_audit_manifest_v1.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit lexical near-duplicate and split-leakage candidates without model evaluation."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--phase0-manifest",
        type=Path,
        default=ROOT / "research/phase0/nid_5class_split_manifest_v1.csv",
    )
    parser.add_argument(
        "--normalization-config",
        type=Path,
        default=HERE / "audit_normalization_v1.yaml",
    )
    parser.add_argument("--output-dir", type=Path, default=HERE)
    parser.add_argument("--private-review", type=Path, default=DEFAULT_PRIVATE_REVIEW)
    parser.add_argument(
        "--no-private-review",
        action="store_true",
        help="Skip the external raw-text review CSV (useful for deterministic tests)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    private_review = None if args.no_private_review else args.private_review
    manifest = run_audit(
        args.source,
        args.phase0_manifest,
        args.normalization_config,
        args.output_dir,
        private_review,
    )
    print("LEAKAGE AUDIT: PASS")
    print("ROWS:", manifest["rows"])
    print("CANDIDATE PAIRS >= 0.80:", manifest["candidate_pairs"])
    print("PHASE 0 EXACT GROUPS:", manifest["exact_duplicates"]["phase0_normalized"]["groups"])
    print("AUDIT-NORM EXACT GROUPS:", manifest["exact_duplicates"]["audit_normalized"]["groups"])
    if manifest["private_review"]:
        print("PRIVATE REVIEW ROWS:", manifest["private_review"]["rows"])
        print("PRIVATE REVIEW SHA256:", manifest["private_review"]["sha256"])


if __name__ == "__main__":
    main()
