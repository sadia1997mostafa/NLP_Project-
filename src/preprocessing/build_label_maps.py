"""Generate deterministic integer label maps from the frozen contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "labels.yaml"
OUTPUT_DIR = ROOT / "contracts" / "label_maps"


def make_map(labels: list[str]) -> dict:
    ordered = sorted(labels)
    return {
        "label_to_id": {label: index for index, label in enumerate(ordered)},
        "id_to_label": {str(index): label for index, label in enumerate(ordered)},
    }


def contract_labels(contract_path: Path = CONTRACT) -> dict[str, list[str]]:
    data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    if data.get("status") != "frozen":
        raise ValueError("Label maps may only be generated from a frozen contract")

    services = list(data.get("services", {}))
    parents: list[str] = []
    intents: list[str] = []
    for service in data.get("services", {}).values():
        for parent_id, parent in service.get("parent_topics", {}).items():
            parents.append(parent_id)
            intents.extend(parent.get("query_topics", {}))

    return {
        "service": services,
        "parent": parents,
        "intent": intents,
        "priority": list(data.get("priority_labels", [])),
    }


def build(output_dir: Path = OUTPUT_DIR) -> dict[str, dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    maps = {task: make_map(labels) for task, labels in contract_labels().items()}
    for task, mapping in maps.items():
        path = output_dir / f"{task}_labels.json"
        path.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return maps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    maps = build(args.output_dir)
    print("Generated label maps:")
    for task, mapping in maps.items():
        print(f"  {task}: {len(mapping['label_to_id'])}")


if __name__ == "__main__":
    main()
