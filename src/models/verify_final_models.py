"""Load-test compact Prothom models and record their frozen-label counts."""

from __future__ import annotations

import gc
import json
from pathlib import Path

from transformers import AutoModelForSequenceClassification

from src.models.hierarchy import conditioned_label_map, hierarchy_index


ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "models/final"
OUTPUT = ROOT / "models/evaluation/final_model_inventory.json"
PRIORITY_CONTRACT = ROOT / "configs/priority_by_intent.json"


def verify(path: Path, expected_labels: int) -> dict:
    required = {"config.json", "model.safetensors", "selection.json"}
    missing = sorted(name for name in required if not (path / name).exists())
    if missing:
        raise FileNotFoundError(f"{path} missing compact artifacts: {missing}")
    model = AutoModelForSequenceClassification.from_pretrained(
        path,
        local_files_only=True,
    )
    actual = int(model.config.num_labels)
    del model
    gc.collect()
    if actual != expected_labels:
        raise ValueError(f"{path}: expected {expected_labels} labels, found {actual}")
    return {
        "path": str(path.relative_to(ROOT)),
        "expected_labels": expected_labels,
        "actual_labels": actual,
        "selection": json.loads((path / "selection.json").read_text(encoding="utf-8")),
        "load_verified": True,
    }


def main() -> None:
    services_to_parents, _, _ = hierarchy_index()
    records = [verify(FINAL / "service", 6)]
    for service, parents in services_to_parents.items():
        records.append(verify(FINAL / "parent" / service, len(parents)))
    for service in services_to_parents:
        records.append(
            verify(
                FINAL / "intent" / service,
                len(conditioned_label_map("intent", service)),
            )
        )
    priority_map = json.loads(PRIORITY_CONTRACT.read_text(encoding="utf-8"))
    if len(priority_map) != 264:
        raise ValueError(f"Expected 264 priority mappings, found {len(priority_map)}")
    invalid_priorities = sorted(set(priority_map.values()) - {"Low", "Medium", "High"})
    if invalid_priorities:
        raise ValueError(f"Invalid priority labels: {invalid_priorities}")

    historical_priority = FINAL / "priority"
    historical_priority_record = None
    if historical_priority.exists():
        selection_path = historical_priority / "selection.json"
        historical_priority_record = {
            "path": str(historical_priority.relative_to(ROOT)),
            "active": False,
            "role": "historical_learned_priority_baseline",
            "selection": (
                json.loads(selection_path.read_text(encoding="utf-8"))
                if selection_path.exists()
                else None
            ),
        }

    payload = {
        "status": "active_partner_a_runtime_verified",
        "test_data_used": False,
        "active_neural_model_count": len(records),
        "active_neural_models": records,
        "priority": {
            "method": "deterministic_from_intent",
            "contract": str(PRIORITY_CONTRACT.relative_to(ROOT)),
            "intent_count": len(priority_map),
            "high_intents": sorted(
                intent for intent, priority in priority_map.items() if priority == "High"
            ),
        },
        "historical_experiments": {
            "learned_priority_model": historical_priority_record,
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
