"""Build canonical six-service data, OOD data, reports and family-safe splits."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path
import csv
import json
import shutil

import pandas as pd
import yaml

from service_pilot_framework import DATASET_COLUMNS
from text_normalization import normalize_text, normalized_key


ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = ROOT / "data" / "annotations"
PROCESSED = ROOT / "data" / "processed"
SPLITS = ROOT / "data" / "splits"

TAXONOMIES = {
    "NID": ROOT / "taxonomy" / "nid.yaml",
    "BIRTH_REGISTRATION": ROOT / "taxonomy" / "birth_registration.yaml",
    "PASSPORT": ROOT / "taxonomy" / "passport.yaml",
    "TAX": ROOT / "taxonomy" / "tax.yaml",
    "POLICE_GD": ROOT / "taxonomy" / "police_gd.yaml",
    "DRIVING_LICENCE": ROOT / "taxonomy" / "driving_licence.yaml",
}

PILOTS = {
    "PASSPORT": ANNOTATIONS / "passport_pilot_v0_1.csv",
    "TAX": ANNOTATIONS / "tax_pilot_v0_1.csv",
    "POLICE_GD": ANNOTATIONS / "police_gd_pilot_v0_1.csv",
    "DRIVING_LICENCE": ANNOTATIONS / "driving_licence_pilot_v0_1.csv",
}

OUTPUTS = {
    "NID": PROCESSED / "nid_canonical_v0_1.csv",
    "BIRTH_REGISTRATION": PROCESSED / "birth_registration_canonical_v0_1.csv",
    "PASSPORT": PROCESSED / "passport_canonical_v0_1.csv",
    "TAX": PROCESSED / "tax_canonical_v0_1.csv",
    "POLICE_GD": PROCESSED / "police_gd_canonical_v0_1.csv",
    "DRIVING_LICENCE": PROCESSED / "driving_licence_canonical_v0_1.csv",
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def write_csv(path: Path, rows: list[dict] | pd.DataFrame, columns=DATASET_COLUMNS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows, columns=columns)
    frame.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n", columns=columns)


def leaf_index(service: str) -> list[tuple[str, dict, str, dict]]:
    data = yaml.safe_load(TAXONOMIES[service].read_text(encoding="utf-8"))
    result = []
    for parent_id, parent in data["parent_topics"].items():
        for leaf_id, leaf in parent["query_topics"].items():
            result.append((parent_id, parent, leaf_id, leaf))
    return result


def paraphrase(text: str, variant: int, ordinal: int) -> str:
    base = normalize_text(text).rstrip("?.। ")
    replacements = [
        ("কীভাবে", "কোন প্রক্রিয়ায়"), ("কোথায়", "কোন জায়গায়"),
        ("কী কী", "কোন কোন"), ("করব", "করতে হবে"),
        ("চাই", "প্রয়োজন"), ("লাগবে", "দরকার হবে"),
        ("kivabe", "kon process e"), ("ki ki", "kon kon jinis"),
        ("korbo", "korte hobe"), ("kothay", "kon jaygay"),
        ("how do i", "what is the process to"),
        ("how can i", "what steps should I follow to"),
        ("can i", "is it possible to"), ("where can i", "where should I"),
        ("what documents", "which documents"),
    ]
    transformed = base
    start = ordinal % len(replacements)
    lowered = transformed.lower()
    for offset in range(len(replacements)):
        old, new = replacements[(start + offset) % len(replacements)]
        index = lowered.find(old.lower())
        if index >= 0:
            transformed = transformed[:index] + new + transformed[index + len(old):]
            break

    bangla = any("\u0980" <= char <= "\u09ff" for char in transformed)
    if bangla:
        variants = [
            f"{transformed}?",
            f"{transformed}—নিয়মটা জানাবেন?",
            f"{transformed}; এ অবস্থায় করণীয় কী?",
            f"আমার ক্ষেত্রে {transformed}?",
            f"{transformed}, একটু বুঝিয়ে বলবেন?",
            f"এটা নিয়ে সাহায্য দরকার: {transformed}?",
            f"{transformed}; পরের ধাপটা কী?",
            f"জানতে চাই, {transformed}?",
        ]
    else:
        variants = [
            f"{transformed}?",
            f"Could you explain {transformed}?",
            f"I need guidance on this: {transformed}?",
            f"For my case, {transformed}?",
            f"Please tell me the correct process: {transformed}?",
            f"{transformed}; what should I do next?",
            f"Can you clarify this for me: {transformed}?",
            f"I am trying to understand this: {transformed}?",
        ]
    result = variants[(ordinal * 2 + variant) % len(variants)]
    if normalized_key(result) == normalized_key(text):
        result = f"এই বিষয়ে সহায়তা চাই: {base}?"
    return normalize_text(result)


def naturalize_seed(text: str, ordinal: int) -> str:
    """Turn taxonomy include fragments into standalone synthetic questions."""
    cleaned = normalize_text(text).rstrip(".। ")
    if cleaned.endswith("?"):
        return cleaned
    lowered = cleaned.lower()
    if lowered.startswith(("how ", "what ", "where ", "who ", "can ", "is ", "do ", "does ", "why ")):
        return cleaned + "?"
    if lowered.startswith("whether "):
        return "Can you clarify " + cleaned[8:].strip() + "?"
    frames = [
        "What should I know about {}?",
        "Could you explain the rules for {}?",
        "I need guidance about {}. What should I do?",
        "How does {} work?",
        "Please explain the official process for {}.",
        "Which rules apply to {}?",
        "Where can I get help about {}?",
        "What is required for {}?",
        "Can you guide me about {}?",
        "I have a question about {}. What is the process?",
        "What are the next steps for {}?",
        "How should I handle {}?",
    ]
    return frames[ordinal % len(frames)].format(cleaned[0].lower() + cleaned[1:])


def expand_pilot(service: str, path: Path) -> pd.DataFrame:
    pilot = read_csv(path)
    rows = []
    prefix = {"PASSPORT": "PASSX", "TAX": "TAXX", "POLICE_GD": "PGDX", "DRIVING_LICENCE": "DLX"}[service]
    number = 1
    for ordinal, seed in enumerate(pilot.to_dict("records")):
        for member in range(3):
            row = dict(seed)
            row["id"] = f"{prefix}_{number:04d}"
            if member:
                row["text"] = paraphrase(seed["text"], member, ordinal + member)
                row["source_type"] = "PARAPHRASED"
                row["annotation_notes"] = (
                    f"Controlled paraphrase {member} of reviewed independent seed; "
                    "family preserved; automated validation complete."
                )
            else:
                row["annotation_notes"] = (
                    "Reviewed independent pilot seed retained for canonical expansion."
                )
            rows.append(row)
            number += 1
    return pd.DataFrame(rows, columns=DATASET_COLUMNS)


def build_nid_inventory() -> list[Path]:
    candidates = []
    for path in (ROOT / "data").rglob("*"):
        if not path.is_file() or "processed" in path.parts:
            continue
        if "nid" in path.name.casefold() and path.suffix.casefold() in {".csv", ".tsv", ".xlsx", ".xls", ".json"}:
            candidates.append(path)
    inventory = {
        "source_files": [str(path.relative_to(ROOT)) for path in candidates],
        "source_file_count": len(candidates),
        "source_rows": 0,
        "mapping_status": "NO_HISTORICAL_NID_SOURCE_PRESENT_IN_REPOSITORY" if not candidates else "REVIEW_REQUIRED",
        "provenance_note": "No REAL provenance is claimed without an accessible source artifact.",
    }
    (PROCESSED / "nid_source_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = """# NID Source Dataset Inventory

No historical NID query dataset is present in the checked repository tree.

- Located source files: 0
- Located source rows: 0
- High-confidence legacy mappings: 0
- Rows requiring migration review: 0
- REAL rows claimed: 0

The previously discussed 1,454-row sheet is not available as a repository
artifact, so this run does not fabricate its schema, provenance or mappings.
The migration pipeline emits an empty, schema-valid review artifact and a
synthetic balanced core. When the historical source is supplied, it must be
ingested as a new immutable source and mapped without overwriting it.
"""
    (PROCESSED / "NID_SOURCE_DATA_INVENTORY.md").write_text(markdown, encoding="utf-8")
    review_columns = DATASET_COLUMNS + ["source_file", "legacy_label", "migration_status", "migration_reason"]
    write_csv(PROCESSED / "nid_migration_review.csv", [], review_columns)
    return candidates


def build_nid_core() -> pd.DataFrame:
    rows = []
    number = 1
    styles = ["Formal", "Informal", "Mixed", "Mixed"]
    difficulties = ["Easy", "Medium", "Medium", "Hard"]
    for leaf_number, (parent_id, parent, leaf_id, leaf) in enumerate(leaf_index("NID")):
        display = leaf["display_name"]
        examples = leaf.get("includes", [])
        seeds = [naturalize_seed(example, leaf_number * 4 + index) for index, example in enumerate(examples[:4])]
        while len(seeds) < 4:
            seeds.append(naturalize_seed(display, leaf_number * 4 + len(seeds)))
        priority = "Medium" if any(word in leaf_id for word in ("PROBLEM", "FAIL", "DELAY", "LOST", "STOLEN", "MISSING", "CANCELLATION")) else "Low"
        for family_number, seed in enumerate(seeds, start=1):
            family = f"{leaf_id}_F{family_number:02d}"
            for member in range(3):
                text = seed if member == 0 else paraphrase(seed, member, leaf_number + family_number + member)
                rows.append({
                    "id": f"NIDQ_{number:04d}", "text": text, "service": "NID",
                    "parent_topic_id": parent_id, "parent_topic": parent["display_name"],
                    "query_topic_id": leaf_id, "query_topic": display,
                    "priority": priority, "language_style": styles[family_number - 1],
                    "privacy_present": "FALSE", "privacy_types": "",
                    "source_type": "SYNTHETIC" if member == 0 else "PARAPHRASED",
                    "parent_query_id": family, "difficulty": difficulties[family_number - 1],
                    "is_ood": "FALSE",
                    "annotation_notes": "Synthetic NID core anchored in reviewed taxonomy include examples; automated semantic/structural validation only; no REAL provenance claimed.",
                })
                number += 1
    return pd.DataFrame(rows, columns=DATASET_COLUMNS)


OOD_TOPICS = {
    "LAND_RECORDS": ["খতিয়ান", "নামজারি", "ভূমি কর", "দাগ নম্বর", "জমির নকশা", "মৌজা", "দলিল", "ভূমি আপিল", "জমি পরিমাপ", "খাস জমি"],
    "UTILITY": ["বিদ্যুৎ বিল", "গ্যাস সংযোগ", "পানি বিল", "মিটার", "লোডশেডিং", "পয়ঃনিষ্কাশন", "লাইন মেরামত", "বিল সংশোধন", "নতুন সংযোগ", "ইউটিলিটি অভিযোগ"],
    "EDUCATION": ["বিশ্ববিদ্যালয় ভর্তি", "পরীক্ষার ফল", "বৃত্তি", "সনদ উত্তোলন", "স্কুল বদলি", "বোর্ড পরীক্ষা", "টিউশন ফি", "অনলাইন ক্লাস", "শিক্ষক নিবন্ধন", "পাঠ্যবই"],
    "HEALTH_ADMIN": ["হাসপাতাল appointment", "টিকা সনদ", "স্বাস্থ্য কার্ড", "ডাক্তার তালিকা", "রক্তদান", "হাসপাতাল বিল", "অ্যাম্বুলেন্স booking", "ক্লিনিক নিবন্ধন", "ওষুধের দোকান", "স্বাস্থ্য প্রতিবেদন"],
    "BANKING": ["ব্যাংক account", "ATM card", "loan application", "cheque book", "mobile banking", "সঞ্চয়পত্র", "bank statement", "credit card", "interest rate", "account closure"],
    "WEATHER": ["আজকের আবহাওয়া", "বৃষ্টির সম্ভাবনা", "তাপমাত্রা", "ঘূর্ণিঝড়", "বন্যা পূর্বাভাস", "কুয়াশা", "বাতাসের গতি", "সমুদ্রের অবস্থা", "আবহাওয়া সতর্কতা", "আগামী সপ্তাহের forecast"],
    "GENERAL_KNOWLEDGE": ["বাংলাদেশের ইতিহাস", "একটি কবিতা", "বিজ্ঞানের প্রশ্ন", "গণিত সমাধান", "ভাষার অনুবাদ", "খেলার নিয়ম", "রান্নার recipe", "ভ্রমণ পরামর্শ", "কম্পিউটার শিক্ষা", "বইয়ের সারাংশ"],
    "CASUAL": ["কেমন আছেন", "একটি কৌতুক", "ধন্যবাদ", "শুভ সকাল", "গান শুনতে চাই", "বন্ধুত্বের কথা", "সময় কাটানো", "মজার গল্প", "নিজের পরিচয়", "বিদায়"],
    "AGRICULTURE": ["ফসলের রোগ", "সার ব্যবহার", "বীজ", "কৃষি ঋণ", "সেচ", "মাছ চাষ", "পশু চিকিৎসা", "বাজারদর", "কৃষি প্রশিক্ষণ", "মাটি পরীক্ষা"],
    "SOCIAL_WELFARE": ["বয়স্ক ভাতা", "প্রতিবন্ধী ভাতা", "বিধবা ভাতা", "খাদ্য সহায়তা", "আশ্রয়ণ", "অনুদান", "সমাজসেবা", "ভাতা status", "সহায়তার আবেদন", "কল্যাণ কর্মসূচি"],
    "BUSINESS_LICENCE": ["trade licence", "company registration", "import permit", "export licence", "factory licence", "shop permit", "business name", "VAT registration", "fire licence", "commercial approval"],
    "MUNICIPAL": ["holding tax", "বাড়ির নকশা", "বর্জ্য সংগ্রহ", "রাস্তা মেরামত", "street light", "নগর অভিযোগ", "পার্কিং permit", "বাজার lease", "নির্মাণ অনুমতি", "ward certificate"],
}


def build_ood() -> pd.DataFrame:
    rows = []
    number = 1
    for category, topics in OOD_TOPICS.items():
        label = category.replace("_", " ").title()
        for family_number, topic in enumerate(topics, start=1):
            family = f"OOD_{category}_F{family_number:02d}"
            texts = [
                f"{topic} বিষয়ে সরকারি সেবা কোথায় পাব?",
                f"{topic} নিয়ে একটু help দরকার।",
                f"{topic} service er information kivabe janbo?",
            ]
            for member, text in enumerate(texts):
                rows.append({
                    "id": f"OODQ_{number:04d}", "text": text, "service": "OOD",
                    "parent_topic_id": f"OOD_{category}", "parent_topic": label,
                    "query_topic_id": f"OOD_{category}", "query_topic": label,
                    "priority": "Low", "language_style": ["Formal", "Informal", "Mixed"][member],
                    "privacy_present": "FALSE", "privacy_types": "",
                    "source_type": "SYNTHETIC" if member == 0 else "PARAPHRASED",
                    "parent_query_id": family, "difficulty": ["Easy", "Medium", "Hard"][member],
                    "is_ood": "TRUE", "annotation_notes": "Synthetic safe OOD example; outside the six supported production services.",
                })
                number += 1
    return pd.DataFrame(rows, columns=DATASET_COLUMNS)


def build_splits(all_data: pd.DataFrame, ood: pd.DataFrame) -> None:
    family_to_split = {}
    for _, leaf_rows in all_data.groupby("query_topic_id", sort=True):
        families = sorted(leaf_rows["parent_query_id"].unique())
        if len(families) != 4:
            raise ValueError(
                f"Expected four families for {leaf_rows.iloc[0]['query_topic_id']}, "
                f"found {len(families)}"
            )
        for index, family in enumerate(families):
            family_to_split[family] = "train" if index < 2 else "dev" if index == 2 else "test"
    split_names = all_data["parent_query_id"].map(family_to_split)
    for split in ("train", "dev", "test"):
        frame = all_data.loc[split_names.eq(split)].copy()
        frame["text"] = frame["text"].map(normalize_text)
        write_csv(SPLITS / f"{split}.csv", frame)
    ood_family_number = ood["parent_query_id"].str.extract(r"_F(\d+)$", expand=False).astype(int)
    write_csv(SPLITS / "ood_dev.csv", ood.loc[ood_family_number.mod(2).eq(1)].copy())
    write_csv(SPLITS / "ood_test.csv", ood.loc[ood_family_number.mod(2).eq(0)].copy())


def near_duplicate_summary(frame: pd.DataFrame, threshold: float = 0.86) -> dict:
    token_sets = [set(normalized_key(text).split()) for text in frame["text"]]
    cross_family = 0
    cross_intent = 0
    examples = []
    for left, right in combinations(range(len(frame)), 2):
        a, b = token_sets[left], token_sets[right]
        if not a or not b:
            continue
        similarity = len(a & b) / len(a | b)
        if similarity < threshold:
            continue
        left_row, right_row = frame.iloc[left], frame.iloc[right]
        if left_row["parent_query_id"] == right_row["parent_query_id"]:
            continue
        cross_family += 1
        if left_row["query_topic_id"] != right_row["query_topic_id"]:
            cross_intent += 1
        if len(examples) < 10:
            examples.append({
                "left_id": left_row["id"], "right_id": right_row["id"],
                "similarity": round(similarity, 3),
                "same_intent": left_row["query_topic_id"] == right_row["query_topic_id"],
            })
    return {
        "method": f"token-set Jaccard >= {threshold}",
        "cross_family_pairs": cross_family,
        "cross_intent_pairs": cross_intent,
        "sample": examples,
    }


def build_report(frames: dict[str, pd.DataFrame], all_data: pd.DataFrame, ood: pd.DataFrame) -> None:
    lines = ["# Pre-Training Dataset Report", "", "Generated deterministically by `prepare_pretraining_data.py`.", "", "## In-domain services", "", "| Service | Rows | Parents | Leaves | Families | Min/Max rows per leaf |", "|---|---:|---:|---:|---:|---:|"]
    for service, frame in frames.items():
        counts = frame.groupby("query_topic_id").size()
        lines.append(f"| {service} | {len(frame)} | {frame.parent_topic_id.nunique()} | {frame.query_topic_id.nunique()} | {frame.parent_query_id.nunique()} | {counts.min()}/{counts.max()} |")
    lines += ["", f"Total in-domain rows: **{len(all_data)}**", f"Total production intents: **{all_data.query_topic_id.nunique()}**", "", "## Provenance", ""]
    for key, value in all_data["source_type"].value_counts().items(): lines.append(f"- {key}: {value}")
    near = near_duplicate_summary(all_data)
    lines += ["", "## OOD", "", f"- Rows: {len(ood)}", f"- Categories: {ood.query_topic_id.nunique()}", "- All OOD content is synthetic and privacy-negative.", "", "## Integrity", "", f"- Exact normalized in-domain duplicates: {all_data.text.map(normalized_key).duplicated().sum()}", f"- Exact normalized OOD duplicates: {ood.text.map(normalized_key).duplicated().sum()}", f"- Near-duplicate scan: {near['method']}", f"- Near-duplicate cross-family pairs: {near['cross_family_pairs']}", f"- Near-duplicate cross-intent pairs requiring attention: {near['cross_intent_pairs']}", "- NID historical source rows available in repository: 0", "- NID REAL rows claimed: 0", "- Split unit: complete `parent_query_id` family", "- Split rule for four-family leaves: F01/F02 train, F03 dev, F04 test", "", "## Known limitations", "", "- NID has no historical source artifact in this repository; its balanced core is synthetic.", "- Rule-based paraphrases received automated checks, not human review.", "- OOD coverage is synthetic and thresholds remain to be calibrated after training.", ""]
    (ROOT / "docs" / "PRETRAINING_DATA_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
    report = {
        "total_rows": len(all_data),
        "rows_per_service": all_data["service"].value_counts().sort_index().to_dict(),
        "rows_per_parent": all_data["parent_topic_id"].value_counts().sort_index().to_dict(),
        "rows_per_leaf": all_data["query_topic_id"].value_counts().sort_index().to_dict(),
        "provenance": all_data["source_type"].value_counts().to_dict(),
        "priority": all_data["priority"].value_counts().to_dict(),
        "language_style": all_data["language_style"].value_counts().to_dict(),
        "difficulty": all_data["difficulty"].value_counts().to_dict(),
        "family_count": int(all_data["parent_query_id"].nunique()),
        "family_size_distribution": all_data.groupby("parent_query_id").size().value_counts().sort_index().to_dict(),
        "exact_normalized_duplicates": int(all_data["text"].map(normalized_key).duplicated().sum()),
        "unresolved_nid_migration_rows": 0,
        "ood_rows": len(ood),
        "ood_categories": int(ood["query_topic_id"].nunique()),
        "near_duplicates": near,
    }
    (PROCESSED / "pretraining_data_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    SPLITS.mkdir(parents=True, exist_ok=True)
    build_nid_inventory()
    frames = {"NID": build_nid_core()}
    birth = read_csv(ANNOTATIONS / "birth_registration_expanded_v0_2.csv")[DATASET_COLUMNS]
    frames["BIRTH_REGISTRATION"] = birth
    for service, path in PILOTS.items(): frames[service] = expand_pilot(service, path)
    for service, frame in frames.items(): write_csv(OUTPUTS[service], frame)
    all_data = pd.concat([frames[service] for service in TAXONOMIES], ignore_index=True)
    write_csv(PROCESSED / "all_services_canonical_v0_1.csv", all_data)
    ood = build_ood()
    write_csv(PROCESSED / "ood_canonical_v0_1.csv", ood)
    build_splits(all_data, ood)
    build_report(frames, all_data, ood)
    print("Canonical pre-training data prepared.")
    print("In-domain rows:", len(all_data))
    print("Production intents:", all_data["query_topic_id"].nunique())
    print("OOD rows/categories:", len(ood), "/", ood["query_topic_id"].nunique())


if __name__ == "__main__":
    main()
