"""Freeze and validate the canonical Phase 0 five-class NID protocol.

This script does not reconstruct the lost historical experiment. It consumes
an immutable private CSV export and produces only text-free research metadata,
hashes, label mappings, and deterministic split assignments.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROTOCOL_VERSION = "NID-5CLASS-PHASE0-V1"
SEED = 42
EXPECTED_ROWS = 1454
EXPECTED_RAW_SHA256 = (
    "6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa"
)
EXPECTED_NAMED_COLUMNS = [
    "id",
    "text",
    "service",
    "problem",
    "priority",
    "language_style",
    "privacy_present",
    "privacy_types",
    "source_type",
    "parent_id",
    "difficulty",
    "is_ood",
    "annotation_notes",
]
EXPECTED_RAW_HEADER = EXPECTED_NAMED_COLUMNS + ["", ""]
LABEL_SPECS = [
    (0, "NID Information Correction", 267),
    (1, "New NID Registration", 448),
    (2, "Lost/Stolen NID", 236),
    (3, "NID Online Problem", 305),
    (4, "Smart ID Card", 198),
]
SPLITS = ("train", "dev", "test")
RATIOS = {"train": 0.70, "dev": 0.15, "test": 0.15}

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "_private" / "phase0" / "nid_5class_source_v1.csv"
DEFAULT_OUTPUT = Path(__file__).resolve().parent
STARTING_GIT_COMMIT = "0c61617169f4301a73a334b9970adaf18867fc66"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: object) -> str:
    """Phase 0 canonical normalization: string, NFC, whitespace, strip."""
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def compact_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def load_source(path: Path) -> tuple[list[str], list[dict[str, object]]]:
    raw_hash = sha256_file(path)
    if raw_hash != EXPECTED_RAW_SHA256:
        raise ValueError(
            "SOURCE FREEZE MISMATCH: raw SHA-256 is "
            f"{raw_hash}, expected {EXPECTED_RAW_SHA256}"
        )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        columns = next(reader, [])
        if columns != EXPECTED_RAW_HEADER:
            raise ValueError(
                "SOURCE FREEZE MISMATCH: columns changed: "
                f"{columns!r}"
            )
        rows = []
        for source_row_number, cells in enumerate(reader, start=1):
            if len(cells) != len(columns):
                raise ValueError(
                    "SOURCE FREEZE MISMATCH: row width changed at data row "
                    f"{source_row_number}: {len(cells)} != {len(columns)}"
                )
            row: dict[str, object] = {
                column: cells[index]
                for index, column in enumerate(EXPECTED_NAMED_COLUMNS)
            }
            row["__raw_cells__"] = cells
            rows.append(row)
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(
            f"SOURCE FREEZE MISMATCH: rows={len(rows)}, expected={EXPECTED_ROWS}"
        )
    observed = Counter(str(row["problem"]) for row in rows)
    expected = Counter({name: count for _, name, count in LABEL_SPECS})
    if observed != expected:
        raise ValueError(
            "SOURCE FREEZE MISMATCH: label inventory changed: "
            f"{dict(observed)!r}"
        )
    return columns, rows


def canonical_content_sha256(columns: list[str], rows: list[dict[str, object]]) -> str:
    payload = {
        "columns": columns,
        "rows": [row["__raw_cells__"] for row in rows],
    }
    return sha256_bytes(compact_json_bytes(payload))


def pii_screen(rows: list[dict[str, object]]) -> dict:
    bangla_digits = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    patterns = {
        "NID_NUMBER_LIKE": re.compile(r"(?<!\d)(?:\d[ -]?){10,17}(?!\d)"),
        "BANGLADESH_PHONE_LIKE": re.compile(
            r"(?<!\d)(?:(?:\+?880|0)[ -]?)?1[3-9](?:[ -]?\d){8}(?!\d)"
        ),
        "EMAIL_LIKE": re.compile(
            r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])"
        ),
        "PASSPORT_IDENTIFIER_LIKE": re.compile(
            r"(?i)(?:passport|পাসপোর্ট)\s*(?:no|number|নং|নম্বর)?"
            r"\s*[:#-]?\s*[A-Z]{1,2}\d{7,8}"
        ),
        "DOB_IDENTIFIER_LIKE": re.compile(
            r"(?i)(?:dob|date of birth|birth date|জন্ম\s*তারিখ)\s*[:#-]?\s*"
            r"(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|"
            r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"
        ),
    }
    summary = {}
    any_flagged: set[int] = set()
    for name, pattern in patterns.items():
        row_count = 0
        match_count = 0
        for row_number, row in enumerate(rows, start=1):
            text = " ".join(str(value) for value in row["__raw_cells__"])
            text = text.translate(bangla_digits)
            matches = list(pattern.finditer(text))
            if matches:
                row_count += 1
                match_count += len(matches)
                any_flagged.add(row_number)
        summary[name] = {
            "rows_flagged": row_count,
            "total_matches": match_count,
        }
    unnamed_nonempty_rows = sum(
        any(str(value) for value in row["__raw_cells__"][-2:]) for row in rows
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "scan_scope": "all 15 raw source cells per row",
        "scan_type": "conservative heuristic; no matched values are retained",
        "patterns": summary,
        "unique_rows_flagged": len(any_flagged),
        "unnamed_trailing_columns": 2,
        "rows_with_nonempty_unnamed_trailing_cells": unnamed_nonempty_rows,
        "manual_review_recommended": bool(any_flagged) or unnamed_nonempty_rows > 0,
        "manual_review_reason": (
            "Populated unnamed trailing source columns require owner review; "
            "their values remain only in the private snapshot and row hashes."
            if unnamed_nonempty_rows
            else "Heuristic sensitive-pattern match found."
            if any_flagged
            else "None from this heuristic screen."
        ),
        "limitations": (
            "A zero heuristic count does not prove that the source is free of all "
            "personal or sensitive information."
        ),
    }


def largest_remainder(total: int) -> dict[str, int]:
    raw = {split: total * RATIOS[split] for split in SPLITS}
    targets = {split: math.floor(raw[split]) for split in SPLITS}
    remaining = total - sum(targets.values())
    order = sorted(
        SPLITS,
        key=lambda split: (-(raw[split] - targets[split]), SPLITS.index(split)),
    )
    for split in order[:remaining]:
        targets[split] += 1
    return targets


def build_records(
    columns: list[str], rows: list[dict[str, object]]
) -> tuple[list[dict], dict[str, list[dict]], dict]:
    label_to_id = {name: label_id for label_id, name, _ in LABEL_SPECS}
    records = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    for source_row_number, row in enumerate(rows, start=1):
        normalized = normalize_text(row["text"])
        normalized_hash = sha256_bytes(normalized.encode("utf-8"))
        row_hash = sha256_bytes(
            compact_json_bytes(row["__raw_cells__"])
        )
        record = {
            "sample_id": f"NID5-V1-{source_row_number:06d}",
            "source_row_number": source_row_number,
            "label_id": label_to_id[str(row["problem"])],
            "label_name": str(row["problem"]),
            "group_id": f"NID5-G-{normalized_hash}",
            "normalized_text_sha256": normalized_hash,
            "row_sha256": row_hash,
        }
        records.append(record)
        grouped[normalized_hash].append(record)

    duplicate_groups = [members for members in grouped.values() if len(members) > 1]
    conflicts = [
        members
        for members in duplicate_groups
        if len({member["label_name"] for member in members}) > 1
    ]
    duplicate_summary = {
        "normalized_duplicate_groups": len(duplicate_groups),
        "rows_in_duplicate_groups": sum(len(group) for group in duplicate_groups),
        "cross_label_conflict_groups": len(conflicts),
        "label_conflict": bool(conflicts),
        "conflict_policy": (
            "LABEL CONFLICT retained without relabeling; every exact-normalized-text "
            "group is assigned wholly to one split."
        ),
    }
    return records, grouped, duplicate_summary


def split_groups(grouped: dict[str, list[dict]]) -> dict[str, str]:
    label_targets = {
        name: largest_remainder(count) for _, name, count in LABEL_SPECS
    }
    total_targets = largest_remainder(EXPECTED_ROWS)
    label_counts = {
        name: {split: 0 for split in SPLITS} for _, name, _ in LABEL_SPECS
    }
    total_counts = {split: 0 for split in SPLITS}

    def group_sort_key(item: tuple[str, list[dict]]) -> tuple:
        normalized_hash, members = item
        labels = {member["label_name"] for member in members}
        seeded = sha256_bytes(f"{SEED}|{normalized_hash}".encode("utf-8"))
        return (-int(len(labels) > 1), -len(members), seeded)

    assignments: dict[str, str] = {}
    for normalized_hash, members in sorted(grouped.items(), key=group_sort_key):
        additions = Counter(member["label_name"] for member in members)
        candidates = []
        for split in SPLITS:
            total_after = total_counts[split] + len(members)
            total_overshoot = max(0, total_after - total_targets[split])
            label_overshoot = sum(
                max(
                    0,
                    label_counts[label][split]
                    + additions[label]
                    - label_targets[label][split],
                )
                for label in additions
            )
            overshoot = total_overshoot + label_overshoot

            score = 0.0
            for _, label, _ in LABEL_SPECS:
                for candidate_split in SPLITS:
                    count = label_counts[label][candidate_split]
                    if candidate_split == split:
                        count += additions[label]
                    target = label_targets[label][candidate_split]
                    score += ((count - target) / max(target, 1)) ** 2
            for candidate_split in SPLITS:
                count = total_counts[candidate_split]
                if candidate_split == split:
                    count += len(members)
                target = total_targets[candidate_split]
                score += ((count - target) / max(target, 1)) ** 2

            tie = sha256_bytes(
                f"{SEED}|{normalized_hash}|{split}".encode("utf-8")
            )
            candidates.append((overshoot, score, tie, split))

        chosen = min(candidates)[-1]
        assignments[normalized_hash] = chosen
        total_counts[chosen] += len(members)
        for label, count in additions.items():
            label_counts[label][chosen] += count

    return assignments


def validate_assignments(
    records: list[dict], grouped: dict[str, list[dict]], assignments: dict[str, str]
) -> None:
    if len(records) != EXPECTED_ROWS:
        raise ValueError("Not all source rows became records")
    if len({record["sample_id"] for record in records}) != EXPECTED_ROWS:
        raise ValueError("Sample IDs are not unique")
    if set(assignments) != set(grouped):
        raise ValueError("Split assignments do not cover every normalized group")
    split_ids = {
        split: {
            member["sample_id"]
            for normalized_hash, members in grouped.items()
            if assignments[normalized_hash] == split
            for member in members
        }
        for split in SPLITS
    }
    if any(split_ids[a] & split_ids[b] for a in SPLITS for b in SPLITS if a < b):
        raise ValueError("Sample overlap exists between splits")
    if set().union(*split_ids.values()) != {
        record["sample_id"] for record in records
    }:
        raise ValueError("Split union does not equal the source sample set")
    split_hashes = {
        split: {
            normalized_hash
            for normalized_hash, chosen in assignments.items()
            if chosen == split
        }
        for split in SPLITS
    }
    if any(
        split_hashes[a] & split_hashes[b]
        for a in SPLITS
        for b in SPLITS
        if a < b
    ):
        raise ValueError("Normalized-text hash overlap exists between splits")
    if assignments != split_groups(grouped):
        raise ValueError("Deterministic split rerun did not reproduce assignments")


def manifest_bytes(records: list[dict], assignments: dict[str, str]) -> bytes:
    from io import StringIO

    columns = [
        "sample_id",
        "source_row_number",
        "label_id",
        "label_name",
        "split",
        "group_id",
        "normalized_text_sha256",
        "row_sha256",
    ]
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for record in records:
        output = dict(record)
        output["split"] = assignments[record["normalized_text_sha256"]]
        writer.writerow({column: output[column] for column in columns})
    return buffer.getvalue().encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def preprocessing_yaml() -> str:
    return """protocol_version: \"NID-5CLASS-PHASE0-V1\"
status: \"phase0_canonical_protocol\"
historical_reconstruction: false
input_field: \"text\"
output_field: \"normalized_text\"
steps:
  - order: 1
    operation: \"convert_to_string\"
  - order: 2
    operation: \"unicode_normalization\"
    form: \"NFC\"
  - order: 3
    operation: \"collapse_consecutive_whitespace\"
    replacement: \"single ASCII space\"
  - order: 4
    operation: \"strip_leading_trailing_whitespace\"
explicitly_not_applied:
  - \"lowercasing\"
  - \"transliteration\"
  - \"punctuation deletion\"
  - \"number removal\"
  - \"stemming\"
  - \"stopword removal\"
  - \"aggressive Bangla normalization\"
  - \"augmentation\"
note: >
  This is the new Phase 0 canonical protocol. It is not recovered historical
  preprocessing and must not be described as such.
"""


def evaluation_contract() -> str:
    return """# NID Five-Class Evaluation Contract v1

## Historical remembered evaluation

- IID Macro-F1: **96.36%**
- Shift Macro-F1: **82.64%**
- Shift gap: **13.72 percentage points**
- Status: **UNVERIFIED HISTORICAL REFERENCE**

These values have not been reproduced. Their original split, model, checkpoint,
predictions, metric implementation and shifted dataset were not recovered.

## New canonical Phase 0 IID evaluation

Protocol: `NID-5CLASS-PHASE0-V1`

- Training: rows where manifest `split == train`
- Model selection and tuning: rows where manifest `split == dev`
- Final IID evaluation: rows where manifest `split == test`
- Primary metric: Macro-F1
- Secondary metrics: accuracy, macro precision, macro recall, per-class
  precision/recall/F1, and confusion matrix

The TEST split must not be used for model selection, hyperparameter tuning,
threshold tuning, data editing, label revision, or split revision.

## Distribution-shift evaluation

Historical shifted dataset: **NOT RECOVERED**.

No replacement shift set is invented in Phase 0. Canonical distribution-shift
challenge sets will be constructed and frozen during Phase 1.

The remembered 82.64% score must not be compared directly with the new
canonical IID test result as though both used the same evaluation protocol.
"""


def task_report(
    raw_hash: str,
    canonical_hash: str,
    pii: dict,
    duplicate_summary: dict,
    split_summary: dict,
    manifest_hash: str,
) -> str:
    label_lines = "\n".join(
        f"| {label_id} | `{name}` | {count} |"
        for label_id, name, count in LABEL_SPECS
    )
    split_lines = "\n".join(
        f"| `{name}` | {counts['train']} | {counts['dev']} | {counts['test']} |"
        for name, counts in split_summary["per_label_counts"].items()
    )
    flagged = pii["unique_rows_flagged"]
    return f"""# Phase 0 Task 2 — NID Five-Class Source Freeze

## 1. Scope

This is a **new canonical reproducible baseline**, not a reconstruction of the
lost historical experiment. The remembered 96.36% IID and 82.64% shifted
Macro-F1 values remain unverified references.

## 2. Frozen source identity

- Source: `G:\\My Drive\\NID Query Datasheet.gsheet`
- Content-identical Drive copy: `G:\\My Drive\\Copy of NID Query Datasheet.gsheet`
- Sheet: `Sheet1`
- Private snapshot: `_private/phase0/nid_5class_source_v1.csv`
- Rows: 1,454
- Physical CSV columns: 15 (13 named plus 2 unnamed trailing columns)
- Rows with populated unnamed trailing cells: {pii['rows_with_nonempty_unnamed_trailing_cells']}
- Raw SHA-256: `{raw_hash}`
- Canonical content SHA-256: `{canonical_hash}`

Canonical content hashing serializes an object containing the full ordered raw
header (including both unnamed columns) and all ordered 15-cell rows as compact
UTF-8 JSON (`ensure_ascii=false`, no key sorting). This separates semantic cell
content from CSV quoting/newline serialization. The raw values in the unnamed
columns remain private and are not interpreted as model fields.

## 3. Privacy screen

The aggregate-only heuristic screen flagged {flagged} rows. No matched value or
raw query text is stored in Git metadata. Manual review recommended:
`{str(pii['manual_review_recommended']).upper()}`. A zero heuristic result is
not proof that no sensitive free-form information exists; the raw snapshot
remains private.

## 4. Label freeze

| ID | Label | Count |
|---:|---|---:|
{label_lines}

Total: **1,454**. The Sheet's `parent_id` values are not used as class IDs.

## 5. Canonical normalization

Input is converted to string, normalized to Unicode NFC, consecutive whitespace
is collapsed, and leading/trailing whitespace is stripped. No lowercasing,
transliteration, punctuation/number removal, stemming, stopword removal,
aggressive Bangla normalization, or augmentation is applied.

## 6. Duplicate handling

- Exact normalized duplicate groups: {duplicate_summary['normalized_duplicate_groups']}
- Rows involved: {duplicate_summary['rows_in_duplicate_groups']}
- Cross-label conflict groups: {duplicate_summary['cross_label_conflict_groups']}
- Status: **{'LABEL CONFLICT' if duplicate_summary['label_conflict'] else 'NO LABEL CONFLICT'}**

Conflicting labels are preserved without repair. Every exact normalized-text
group is assigned wholly to one split.

## 7. Split algorithm

Protocol `NID-5CLASS-PHASE0-V1` uses seed 42 and target proportions 70/15/15.
Groups are exact normalized-text hashes. Cross-label and larger groups are
considered first; remaining order is a seeded SHA-256 order. Each group is
greedily placed in the split minimizing target overshoot and normalized squared
deviation from per-label and overall largest-remainder targets. SHA-256 provides
a deterministic tie-break. No model output or expected score affects assignment.

- Train: {split_summary['split_counts']['train']}
- DEV: {split_summary['split_counts']['dev']}
- TEST: {split_summary['split_counts']['test']}

| Label | Train | DEV | TEST |
|---|---:|---:|---:|
{split_lines}

- Cross-split normalized-text overlap: 0
- Manifest SHA-256: `{manifest_hash}`
- Deterministic in-process rerun: PASS

## 8. Evaluation contract

Train only on `train`, select/tune only on `dev`, and evaluate final IID results
once on `test`. Macro-F1 is primary; accuracy, macro precision/recall,
per-class metrics and the confusion matrix are secondary. TEST is prohibited
for model or threshold selection.

## 9. Historically unknown

The historical split, seed, preprocessing, label encoder, training command,
model/checkpoint, predictions, confusion matrix and shifted dataset remain
unknown. This freeze does not claim to recover them.

## 10. Deferred to Phase 1

Phase 1 will construct and freeze independently specified distribution-shift
challenge sets and perform deeper paraphrase-family/near-duplicate leakage
auditing. No shift set is created here.
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze and validate the reproducible five-class Phase 0 NID "
            "source/split protocol without storing raw text in Git artifacts."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Private source CSV (default: repository _private/phase0 snapshot)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory for small research metadata artifacts",
    )
    args = parser.parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    columns, rows = load_source(input_path)
    raw_hash = sha256_file(input_path)
    canonical_hash = canonical_content_sha256(columns, rows)
    pii = pii_screen(rows)
    records, grouped, duplicate_summary = build_records(columns, rows)
    assignments = split_groups(grouped)
    validate_assignments(records, grouped, assignments)

    manifest_data = manifest_bytes(records, assignments)
    rerun_manifest_data = manifest_bytes(records, split_groups(grouped))
    if rerun_manifest_data != manifest_data:
        raise ValueError(
            "Deterministic rerun did not produce a byte-identical manifest"
        )
    manifest_path = output_dir / "nid_5class_split_manifest_v1.csv"
    manifest_path.write_bytes(manifest_data)
    manifest_hash = sha256_bytes(manifest_data)

    per_label_counts = {}
    for _, label, _ in LABEL_SPECS:
        per_label_counts[label] = {
            split: sum(
                1
                for record in records
                if record["label_name"] == label
                and assignments[record["normalized_text_sha256"]] == split
            )
            for split in SPLITS
        }
    split_counts = {
        split: sum(
            len(grouped[normalized_hash])
            for normalized_hash, chosen in assignments.items()
            if chosen == split
        )
        for split in SPLITS
    }
    split_summary = {
        "protocol_version": PROTOCOL_VERSION,
        "seed": SEED,
        "target_proportions": RATIOS,
        "total_rows": len(records),
        "split_counts": split_counts,
        "per_label_counts": per_label_counts,
        "duplicate_group_count": duplicate_summary["normalized_duplicate_groups"],
        "duplicate_rows_involved": duplicate_summary["rows_in_duplicate_groups"],
        "cross_label_conflict_groups": duplicate_summary[
            "cross_label_conflict_groups"
        ],
        "cross_split_duplicate_count": 0,
        "source_raw_sha256": raw_hash,
        "source_canonical_content_sha256": canonical_hash,
        "manifest_sha256": manifest_hash,
        "deterministic_rerun": True,
        "all_samples_assigned_once": True,
        "split_sample_sets_disjoint": True,
        "raw_text_in_manifest": False,
    }

    labels = {
        "protocol_version": PROTOCOL_VERSION,
        "ordering_basis": (
            "Explicit order of taxonomy/nid.yaml source_dataset_mapping"
        ),
        "label_count": len(LABEL_SPECS),
        "total_samples": sum(count for _, _, count in LABEL_SPECS),
        "labels": [
            {
                "label_id": label_id,
                "label_name": name,
                "source_label": name,
                "sample_count": count,
            }
            for label_id, name, count in LABEL_SPECS
        ],
        "parent_id_used_as_class_id": False,
    }

    exported_at = datetime.fromtimestamp(
        input_path.stat().st_mtime, timezone.utc
    ).isoformat()
    source_manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "source_name": "NID Query Datasheet",
        "google_drive_source_path": "G:\\My Drive\\NID Query Datasheet.gsheet",
        "duplicate_drive_source_path": (
            "G:\\My Drive\\Copy of NID Query Datasheet.gsheet"
        ),
        "google_drive_file_id": "1O7Fg5-NaYDGpSDuZR4ELoD2f8vC5QCwIycVSMAuXno4",
        "duplicate_drive_file_id": "1Akj4WeKNH_UAXEh6mPeGM86Kq5i8ZFM0eLNKCTMYjUM",
        "sheet_name": "Sheet1",
        "exported_at_utc": exported_at,
        "export_format": "Google Drive native Sheet export as text/csv",
        "private_frozen_csv_path": str(input_path),
        "raw_file_sha256": raw_hash,
        "canonical_content_sha256": canonical_hash,
        "canonical_content_hash_method": (
            "SHA-256 of compact UTF-8 JSON containing the ordered column list "
            "and ordered raw cell-value matrix; ensure_ascii=false; no key sorting"
        ),
        "row_count": len(rows),
        "raw_column_count": len(columns),
        "named_column_count": len(EXPECTED_NAMED_COLUMNS),
        "column_names": columns,
        "rows_with_nonempty_unnamed_trailing_cells": pii[
            "rows_with_nonempty_unnamed_trailing_cells"
        ],
        "query_column": "text",
        "label_column": "problem",
        "label_count": len(LABEL_SPECS),
        "duplicate_statistics": duplicate_summary,
        "pii_screen_summary_reference": (
            "research/phase0/pii_screen_summary.json"
        ),
        "git_commit_before_task": STARTING_GIT_COMMIT,
        "python_interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "raw_text_in_git_artifacts": False,
    }

    write_json(output_dir / "pii_screen_summary.json", pii)
    write_json(output_dir / "nid_5class_labels_v1.json", labels)
    write_json(output_dir / "nid_5class_split_summary_v1.json", split_summary)
    write_json(output_dir / "nid_5class_source_manifest_v1.json", source_manifest)
    (output_dir / "nid_5class_preprocessing_v1.yaml").write_text(
        preprocessing_yaml(), encoding="utf-8", newline="\n"
    )
    (output_dir / "nid_5class_evaluation_contract_v1.md").write_text(
        evaluation_contract(), encoding="utf-8", newline="\n"
    )
    (output_dir / "PHASE0_TASK2_SOURCE_FREEZE.md").write_text(
        task_report(
            raw_hash,
            canonical_hash,
            pii,
            duplicate_summary,
            split_summary,
            manifest_hash,
        ),
        encoding="utf-8",
        newline="\n",
    )

    print(f"PROTOCOL: {PROTOCOL_VERSION}")
    print(f"SOURCE ROWS: {len(rows)}")
    print(f"LABELS: {len(LABEL_SPECS)}")
    print(f"RAW SHA256: {raw_hash}")
    print(f"CANONICAL CONTENT SHA256: {canonical_hash}")
    print(f"PII FLAGGED ROWS: {pii['unique_rows_flagged']}")
    print(
        "DUPLICATES: "
        f"groups={duplicate_summary['normalized_duplicate_groups']} "
        f"rows={duplicate_summary['rows_in_duplicate_groups']} "
        f"cross_label_conflicts={duplicate_summary['cross_label_conflict_groups']}"
    )
    print(f"SPLITS: {split_counts}")
    print(f"MANIFEST SHA256: {manifest_hash}")
    print("VALIDATION: PASS")


if __name__ == "__main__":
    main()
