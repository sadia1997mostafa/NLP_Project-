"""DEV-safe latency diagnostics for the cached local understanding pipeline."""

from __future__ import annotations

import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "models/evaluation/inference_latency_dev_safe.json"


def timed(callable_):
    start = time.perf_counter()
    value = callable_()
    return value, time.perf_counter() - start


def main() -> None:
    dependency_start = time.perf_counter()
    import torch
    import transformers

    dependency_seconds = time.perf_counter() - dependency_start

    from src.models.inference import (
        FINAL,
        _MODEL_CACHE,
        _tokenizer,
        model_cache_info,
        predict_understanding,
    )

    _MODEL_CACHE.clear()
    _tokenizer.cache_clear()
    _, tokenizer_seconds = timed(_tokenizer)

    component_load_seconds = {}
    for name, path in (
        ("service", FINAL / "service"),
        ("parent_nid", FINAL / "parent" / "NID"),
        ("intent_nid", FINAL / "intent" / "NID"),
        ("priority", FINAL / "priority"),
    ):
        _, elapsed = timed(lambda selected=path: _MODEL_CACHE.get(selected))
        component_load_seconds[name] = elapsed

    component_cache = model_cache_info()
    component_gpu_mebibytes = (
        torch.cuda.memory_allocated() / (1024 * 1024)
        if torch.cuda.is_available()
        else 0.0
    )

    _MODEL_CACHE.clear()
    nid_text = (
        "আমার জাতীয় পরিচয়পত্র NID হারিয়ে গেছে, "
        "replacement-এর আবেদন কীভাবে করব?"
    )
    passport_text = (
        "আমার বাংলাদেশি পাসপোর্টের মেয়াদ শেষ, "
        "passport reissue কীভাবে করব?"
    )

    first, first_seconds = timed(lambda: predict_understanding(nid_text))
    first_cache = model_cache_info()
    first_gpu_mebibytes = (
        torch.cuda.memory_allocated() / (1024 * 1024)
        if torch.cuda.is_available()
        else 0.0
    )
    warm, warm_seconds = timed(lambda: predict_understanding(nid_text))
    warm_cache = model_cache_info()
    different, different_seconds = timed(
        lambda: predict_understanding(passport_text)
    )
    different_cache = model_cache_info()
    peak_gpu_mebibytes = (
        torch.cuda.max_memory_allocated() / (1024 * 1024)
        if torch.cuda.is_available()
        else 0.0
    )

    payload = {
        "scope": "manual DEV-safe smoke queries; no TEST data",
        "device": str(
            torch.device("cuda" if torch.cuda.is_available() else "cpu")
        ),
        "dependency_import_seconds": dependency_seconds,
        "tokenizer_load_seconds": tokenizer_seconds,
        "representative_component_load_seconds": component_load_seconds,
        "component_cache": component_cache,
        "component_gpu_memory_mib": component_gpu_mebibytes,
        "first_call": {
            "seconds": first_seconds,
            "service": first["service"],
            "parent_topic_id": first["parent_topic_id"],
            "query_topic_id": first["query_topic_id"],
            "is_ood": first["is_ood"],
            "cache": first_cache,
            "gpu_memory_mib": first_gpu_mebibytes,
        },
        "same_route_warm_call": {
            "seconds": warm_seconds,
            "service": warm["service"],
            "parent_topic_id": warm["parent_topic_id"],
            "query_topic_id": warm["query_topic_id"],
            "is_ood": warm["is_ood"],
            "cache": warm_cache,
        },
        "different_route_call": {
            "seconds": different_seconds,
            "service": different["service"],
            "parent_topic_id": different["parent_topic_id"],
            "query_topic_id": different["query_topic_id"],
            "is_ood": different["is_ood"],
            "cache": different_cache,
        },
        "peak_gpu_memory_mib": peak_gpu_mebibytes,
        "cache_policy": {
            "shared_tokenizer": True,
            "model_lru_max_size": 4,
            "all_14_models_loaded_together": False,
        },
        "warning": (
            "Latency is an engineering measurement on one Windows/RTX 3060 "
            "machine, not a production benchmark."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
