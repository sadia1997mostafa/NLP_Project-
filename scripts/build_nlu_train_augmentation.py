from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

TRAIN = ROOT / "data/splits/train.csv"
DEV = ROOT / "data/splits/dev.csv"
TEST = ROOT / "data/splits/test.csv"

OUTPUT = ROOT / "data/splits/train_nlu_augmented.csv"
REPORT = ROOT / "data/evaluation/nlu_augmentation_report.json"
BACKUP = ROOT / "data/splits/train_pre_nlu_augmentation.csv"

MODEL = (
    ROOT
    / "models"
    / "answer_generator"
    / "qwen3-4b-instruct-2507.Q4_K_M.gguf"
)

STYLES = [
    "natural_bangla_1",
    "natural_bangla_2",
    "banglish_1",
    "banglish_2",
    "mixed_bn_en",
    "short_conversational",
    "noisy_realistic",
    "contrastive",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip()).casefold()


def load_llm():
    if not MODEL.exists():
        raise FileNotFoundError(
            f"Local Qwen GGUF not found:\n{MODEL}"
        )

    from llama_cpp import Llama

    print("Loading local Qwen once...")
    return Llama(
        model_path=str(MODEL),
        n_ctx=4096,
        n_threads=8,
        verbose=False,
    )


def prompt_for_intent(
    target: pd.DataFrame,
    siblings: list[tuple[str, str]],
) -> str:
    first = target.iloc[0]

    examples = "\n".join(
        f"- {x}" for x in target["text"].astype(str).tolist()
    )

    sibling_text = "\n".join(
        f"- {qid}: {name}"
        for qid, name in siblings
    )

    return f"""
You create TRAINING UTTERANCES for a Bangladeshi government-service
intent classifier.

TARGET
service: {first['service']}
parent: {first['parent_topic']}
intent_id: {first['query_topic_id']}
intent_name: {first['query_topic']}

EXISTING TRAIN EXAMPLES
{examples}

SIBLING INTENTS UNDER THE SAME PARENT
{sibling_text}

Generate EXACTLY 8 new citizen questions for the TARGET intent.

The eight items MUST follow these styles in this exact order:
1. natural Bangla
2. different natural Bangla
3. Banglish / Romanized Bangla
4. different Banglish / Romanized Bangla
5. mixed Bangla-English
6. short conversational query
7. realistic noisy or typo-like query
8. contrastive query that emphasizes what distinguishes the TARGET
   from its sibling intents

Important rules:
- Keep every utterance clearly inside the TARGET intent.
- Do not drift into sibling intents.
- Do not copy the existing examples.
- Do not answer the question.
- Do not invent fees, deadlines, eligibility rules, document lists,
  phone numbers, URLs, office names, or government facts.
- Do not include personal information.
- Make them sound like real citizens, not dataset descriptions.
- Bangladesh usage is preferred.
- Return JSON ONLY.
- Return exactly one JSON array containing exactly 8 strings.
""".strip()


def parse_generation(text: str) -> list[str]:
    text = text.strip()

    # Strip markdown fences if the model adds them.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        raise ValueError("No JSON array found in model output")

    values = json.loads(text[start : end + 1])

    if not isinstance(values, list) or len(values) != 8:
        raise ValueError(
            f"Expected exactly 8 generated strings, got {len(values)}"
        )

    cleaned = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("Generated item is not a string")
        value = re.sub(r"\s+", " ", value.strip())
        if not value:
            raise ValueError("Generated empty utterance")
        cleaned.append(value)

    if len({normalized(x) for x in cleaned}) != 8:
        raise ValueError("Duplicate utterances inside generation")

    return cleaned


def generate(llm, prompt: str) -> list[str]:
    last_error = None

    for attempt in range(3):
        output = llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate precise synthetic NLU training "
                        "utterances and output JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.65 if attempt == 0 else 0.8,
            top_p=0.9,
            max_tokens=700,
        )

        text = output["choices"][0]["message"]["content"]

        try:
            return parse_generation(text)
        except Exception as exc:
            last_error = exc
            print(
                f"  parse retry {attempt + 1}/3: {exc}",
                flush=True,
            )

    raise RuntimeError(f"Generation failed: {last_error}")


def validate(
    original_train: pd.DataFrame,
    augmented: pd.DataFrame,
    dev: pd.DataFrame,
    test: pd.DataFrame,
    dev_hash_before: str,
    test_hash_before: str,
) -> dict:
    counts = augmented.groupby("query_topic_id").size()

    train_families = set(augmented["parent_query_id"].astype(str))
    dev_families = set(dev["parent_query_id"].astype(str))
    test_families = set(test["parent_query_id"].astype(str))

    normalized_rows = augmented.assign(
        _normalized_text=augmented["text"].map(normalized)
    )

    within_intent_duplicates = int(
        normalized_rows.duplicated(
            subset=["query_topic_id", "_normalized_text"]
        ).sum()
    )

    text_label_counts = (
        normalized_rows.groupby("_normalized_text")["query_topic_id"]
        .nunique()
    )

    cross_intent_duplicates = int((text_label_counts > 1).sum())

    dev_hash_after = sha256(DEV)
    test_hash_after = sha256(TEST)

    report = {
        "original_train_rows": int(len(original_train)),
        "added_rows": int(len(augmented) - len(original_train)),
        "augmented_train_rows": int(len(augmented)),
        "unique_intents": int(augmented["query_topic_id"].nunique()),
        "minimum_rows_per_intent": int(counts.min()),
        "maximum_rows_per_intent": int(counts.max()),
        "all_intents_have_14_rows": bool(
            len(counts) == 264 and counts.eq(14).all()
        ),
        "family_overlap_train_dev": len(
            train_families & dev_families
        ),
        "family_overlap_train_test": len(
            train_families & test_families
        ),
        "family_overlap_dev_test": len(
            dev_families & test_families
        ),
        "within_intent_duplicate_texts": within_intent_duplicates,
        "cross_intent_duplicate_texts": cross_intent_duplicates,
        "dev_sha256_before": dev_hash_before,
        "dev_sha256_after": dev_hash_after,
        "test_sha256_before": test_hash_before,
        "test_sha256_after": test_hash_after,
        "dev_unchanged": dev_hash_before == dev_hash_after,
        "test_unchanged": test_hash_before == test_hash_after,
        "source_type_counts": augmented["source_type"]
        .value_counts()
        .to_dict(),
        "service_counts": augmented["service"]
        .value_counts()
        .sort_index()
        .to_dict(),
    }

    report["validation_passed"] = bool(
        report["original_train_rows"] == 1584
        and report["added_rows"] == 2112
        and report["augmented_train_rows"] == 3696
        and report["unique_intents"] == 264
        and report["all_intents_have_14_rows"]
        and report["family_overlap_train_dev"] == 0
        and report["family_overlap_train_test"] == 0
        and report["family_overlap_dev_test"] == 0
        and report["within_intent_duplicate_texts"] == 0
        and report["cross_intent_duplicate_texts"] == 0
        and report["dev_unchanged"]
        and report["test_unchanged"]
    )

    return report


def build() -> None:
    train = pd.read_csv(
        TRAIN,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    dev = pd.read_csv(
        DEV,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    test = pd.read_csv(
        TEST,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    if len(train) != 1584:
        raise ValueError(
            f"Expected original TRAIN=1584 rows, got {len(train)}"
        )

    counts = train.groupby("query_topic_id").size()
    if len(counts) != 264 or not counts.eq(6).all():
        raise ValueError(
            "Expected exactly 264 intents with exactly 6 TRAIN rows each"
        )

    dev_hash = sha256(DEV)
    test_hash = sha256(TEST)

    llm = load_llm()

    new_rows = []
    existing_all = {
        normalized(x)
        for x in pd.concat(
            [train["text"], dev["text"], test["text"]],
            ignore_index=True,
        )
    }

    intent_ids = sorted(train["query_topic_id"].unique())

    for number, intent_id in enumerate(intent_ids, start=1):
        target = train[
            train["query_topic_id"].eq(intent_id)
        ].copy()

        first = target.iloc[0]
        sibling_rows = (
            train[
                train["parent_topic_id"].eq(
                    first["parent_topic_id"]
                )
            ][["query_topic_id", "query_topic"]]
            .drop_duplicates()
        )

        siblings = [
            (row.query_topic_id, row.query_topic)
            for row in sibling_rows.itertuples()
            if row.query_topic_id != intent_id
        ]

        print(
            f"[{number:03d}/264] {intent_id}",
            flush=True,
        )

        base_prompt = prompt_for_intent(target, siblings)

        generated = None
        normalized_generated = None

        for generation_attempt in range(5):
            retry_prompt = base_prompt

            if generation_attempt > 0:
                retry_prompt += """
                
Previous generation contained wording that already exists in the
dataset. Generate a DIFFERENT set of 8 utterances.

Avoid copying or closely repeating any existing example.
Use genuinely different wording while preserving the exact target
intent.
""".rstrip()

            candidate = generate(
                llm,
                retry_prompt,
            )

            candidate_normalized = {
                normalized(x) for x in candidate
            }

            collision = candidate_normalized & existing_all

            if not collision:
                generated = candidate
                normalized_generated = candidate_normalized
                break

            print(
                f"  duplicate retry {generation_attempt + 1}/5: "
                f"{sorted(collision)}",
                flush=True,
            )

            # Explicitly tell the next attempt which wording is forbidden.
            base_prompt += (
                "\n\nDO NOT USE THESE EXISTING UTTERANCES:\n"
                + "\n".join(f"- {x}" for x in sorted(collision))
            )

        if generated is None or normalized_generated is None:
            raise RuntimeError(
                f"{intent_id}: could not generate 8 unique utterances "
                "after 5 attempts"
            )

        existing_all |= normalized_generated

        template = target.iloc[0].to_dict()

        style_to_language = {
            "natural_bangla_1": "Formal",
            "natural_bangla_2": "Informal",
            "banglish_1": "Informal",
            "banglish_2": "Informal",
            "mixed_bn_en": "Mixed",
            "short_conversational": "Informal",
            "noisy_realistic": "Informal",
            "contrastive": "Mixed",
        }

        for idx, (style, text) in enumerate(
            zip(STYLES, generated),
            start=1,
        ):
            row = dict(template)

            row["id"] = f"NLUAUG_{intent_id}_{idx:02d}"
            row["text"] = text
            row["language_style"] = style_to_language[style]
            row["source_type"] = "SYNTHETIC"
            row["parent_query_id"] = (
                f"{intent_id}_AUG_F{idx:02d}"
            )
            row["privacy_present"] = "False"
            row["privacy_types"] = ""
            row["difficulty"] = (
                "Hard" if style == "contrastive" else "Medium"
            )
            row["annotation_notes"] = (
                "TRAIN-only synthetic NLU augmentation; "
                f"augmentation_style={style}; no REAL provenance claimed."
            )

            new_rows.append(row)

    added = pd.DataFrame(new_rows, columns=train.columns)
    augmented = pd.concat(
        [train, added],
        ignore_index=True,
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    augmented.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )

    report = validate(
        train,
        augmented,
        dev,
        test,
        dev_hash,
        test_hash,
    )

    REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print()
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if not report["validation_passed"]:
        raise SystemExit(
            "NLU AUGMENTATION VALIDATION FAILED"
        )

    print()
    print("NLU AUGMENTATION VALIDATION PASSED")
    print("Output:", OUTPUT)


def promote() -> None:
    if not OUTPUT.exists() or not REPORT.exists():
        raise FileNotFoundError(
            "Build and validate augmentation before promotion"
        )

    report = json.loads(
        REPORT.read_text(encoding="utf-8")
    )

    if not report.get("validation_passed"):
        raise RuntimeError(
            "Refusing promotion because validation did not pass"
        )

    if not BACKUP.exists():
        BACKUP.write_bytes(TRAIN.read_bytes())

    TRAIN.write_bytes(OUTPUT.read_bytes())

    print("PROMOTED:", OUTPUT)
    print("BACKUP:", BACKUP)
    print("ACTIVE TRAIN:", TRAIN)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--promote",
        action="store_true",
    )
    args = parser.parse_args()

    if args.promote:
        promote()
    else:
        build()


if __name__ == "__main__":
    main()

