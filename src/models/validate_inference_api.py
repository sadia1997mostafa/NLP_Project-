"""Validate the public inference contract using manually written safe queries."""

from __future__ import annotations

import json
import time
from pathlib import Path

from src.models.hierarchy import conditioned_label_map, only_intent
from src.models.inference import model_cache_info, predict_understanding


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "models/evaluation/inference_api_dev_safe_smoke.json"
SERVICES = {
    "NID",
    "BIRTH_REGISTRATION",
    "PASSPORT",
    "TAX",
    "POLICE_GD",
    "DRIVING_LICENCE",
}
PRIORITIES = {"Low", "Medium", "High"}
EXAMPLES = [
    "জন্ম নিবন্ধন সনদ বাতিলের আবেদন কীভাবে করব?",
    "জন্ম নিবন্ধন certificate-এর আরেকটি copy কীভাবে পাব?",
    "জন্ম নিবন্ধনের official fee কত?",
    "আমার বাংলাদেশি passport-এর মেয়াদ শেষ, reissue কীভাবে করব?",
]


def validate_result(result: dict) -> None:
    service = result["service"]
    parent = result["parent_topic_id"]
    intent = result["query_topic_id"]
    if service not in SERVICES:
        raise AssertionError(f"Unknown service: {service}")
    if parent not in conditioned_label_map("parent", service):
        raise AssertionError(f"{parent} does not belong to {service}")
    if intent not in conditioned_label_map("intent", service, parent):
        raise AssertionError(f"{intent} does not belong to {service}/{parent}")
    if result["priority"] not in PRIORITIES:
        raise AssertionError(f"Unknown priority: {result['priority']}")
    for field in (
        "service_confidence",
        "parent_confidence",
        "intent_confidence",
        "priority_confidence",
        "ood_score",
        "overall_confidence",
    ):
        value = float(result[field])
        if not 0.0 <= value <= 1.0:
            raise AssertionError(f"{field} is out of bounds: {value}")
    expected_ood = result["service_confidence"] < 0.95
    if bool(result["is_ood"]) != expected_ood:
        raise AssertionError("OOD decision does not follow threshold 0.95")
    single = only_intent(service, parent)
    if single:
        if result["intent_routing"] != "deterministic_single_leaf":
            raise AssertionError("Single-leaf parent did not route deterministically")
        if result["query_topic_id"] != single:
            raise AssertionError("Deterministic route returned the wrong leaf")


def main() -> None:
    results = []
    for text in EXAMPLES:
        start = time.perf_counter()
        result = predict_understanding(text)
        elapsed = time.perf_counter() - start
        validate_result(result)
        results.append(
            {
                "input": text,
                "seconds": elapsed,
                "service": result["service"],
                "service_confidence": result["service_confidence"],
                "parent_topic_id": result["parent_topic_id"],
                "query_topic_id": result["query_topic_id"],
                "intent_routing": result["intent_routing"],
                "priority": result["priority"],
                "is_ood": result["is_ood"],
                "overall_confidence": result["overall_confidence"],
            }
        )

    before_repeat = model_cache_info()
    repeated = predict_understanding(EXAMPLES[-1])
    validate_result(repeated)
    after_repeat = model_cache_info()
    if after_repeat["hits"] <= before_repeat["hits"]:
        raise AssertionError("Repeated route did not reuse cached models")

    deterministic_results = [
        row for row in results if row["intent_routing"] == "deterministic_single_leaf"
    ]
    if not deterministic_results:
        raise AssertionError("Smoke queries did not exercise deterministic routing")

    payload = {
        "scope": "manually written DEV-safe examples; no TEST data",
        "status": "passed",
        "examples": results,
        "deterministic_routes_exercised": len(deterministic_results),
        "repeat_cache_hits_added": after_repeat["hits"] - before_repeat["hits"],
        "final_cache": after_repeat,
        "warning": "Semantic predictions are observations, not expected-label tests.",
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
