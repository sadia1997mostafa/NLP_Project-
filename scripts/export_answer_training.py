"""Export source-scoped answer SFT examples without reading official TEST."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.privacy.detection import detect_privacy
from src.response.controller import response_language
from src.response.facts import facts_for, render_fact
from src.response.model_prompt import prompt_messages
from src.retrieval.corpus import load_records


ROOT = Path(__file__).resolve().parents[1]


def _example(question: str, record: dict, language: str) -> dict:
    answer = " ".join(render_fact(unit, language) for unit in facts_for(record))
    return {
        "prompt": prompt_messages(question, record, language),
        "completion": [{"role": "assistant", "content": answer}],
    }


def examples_for_split(split: str) -> list[dict]:
    if split not in {"train", "dev"}:
        raise ValueError("Only frozen train and dev splits are permitted")
    by_topic = {
        record["query_topic_id"]: record
        for record in load_records() if record["query_topic_id"]
    }
    examples = []
    with (ROOT / "data" / "splits" / f"{split}.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            record = by_topic.get(row["query_topic_id"])
            if record is None or row["privacy_present"] != "FALSE" or row["is_ood"] != "FALSE":
                continue
            question = row["text"].strip()
            if detect_privacy(question).privacy_present:
                continue
            language = response_language(question)
            examples.append(_example(question, record, language))
    if split == "train":
        for record in by_topic.values():
            examples.append(_example(
                f"Give me verified guidance for {record['title']}.", record, "en",
            ))
            examples.append(_example(
                f"{record['title']} সম্পর্কে যাচাইকৃত নির্দেশনা দিন।", record, "bn",
            ))
    return examples


def export(output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for split in ("train", "dev"):
        examples = examples_for_split(split)
        if not examples:
            raise ValueError(f"No answer examples in {split}")
        destination = output_dir / f"{split}.jsonl"
        destination.write_text(
            "".join(json.dumps(example, ensure_ascii=False) + "\n" for example in examples),
            encoding="utf-8",
        )
        counts[split] = len(examples)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "answer_generation")
    args = parser.parse_args()
    for split, count in export(args.output_dir).items():
        print(f"{split}: {count} examples")


if __name__ == "__main__":
    main()
