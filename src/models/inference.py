"""Cached Partner A inference API for the hierarchical understanding system."""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Protocol

from src.models.hierarchy import (
    conditioned_label_map,
    contextualize_intent_text,
    load_contract,
    only_intent,
)
from src.models.service_anchors import unique_service_anchor
from src.preprocessing.text_normalization import normalize_text


ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "models/final"
CALIBRATION = ROOT / "models/evaluation/ood_dev_calibration.json"
PRIORITY_BY_INTENT = ROOT / "configs/priority_by_intent.json"


class Predictor(Protocol):
    def predict(self, text: str, top_k: int = 3) -> dict: ...


@dataclass
class UnderstandingPipeline:
    """Dependency-injected lightweight pipeline retained for tests/clients."""

    service_predictor: Predictor
    parent_predictor: Predictor
    intent_predictor: Predictor
    priority_predictor: Predictor
    confidence_threshold: float | None = None
    ood_threshold: float | None = None

    def predict_understanding(self, text: str, top_k: int = 3) -> dict:
        cleaned = normalize_text(text)
        if not cleaned:
            raise ValueError("text must not be empty")
        outputs = {
            "service": self.service_predictor.predict(cleaned, top_k),
            "parent": self.parent_predictor.predict(cleaned, top_k),
            "intent": self.intent_predictor.predict(cleaned, top_k),
            "priority": self.priority_predictor.predict(cleaned, top_k),
        }
        service_confidence = max(float(outputs["service"]["confidence"]), 0.0)
        ood_score = 1.0 - service_confidence
        rejected = (
            self.confidence_threshold is not None
            and service_confidence < self.confidence_threshold
        ) or (
            self.ood_threshold is not None and ood_score >= self.ood_threshold
        )
        return {
            "service": outputs["service"]["label"],
            "service_confidence": service_confidence,
            "parent_topic_id": outputs["parent"]["label"],
            "parent_confidence": float(outputs["parent"]["confidence"]),
            "query_topic_id": outputs["intent"]["label"],
            "query_topic_confidence": float(outputs["intent"]["confidence"]),
            "priority": outputs["priority"]["label"],
            "priority_confidence": float(outputs["priority"]["confidence"]),
            "is_ood": rejected,
            "ood_score": ood_score,
            "alternatives": {
                key: value.get("alternatives", []) for key, value in outputs.items()
            },
        }


@lru_cache(maxsize=1)
def _tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        FINAL / "tokenizer_xlm_roberta_base",
        local_files_only=True,
    )


class _BoundedModelCache:
    """Keep one complete route resident without loading every classifier."""

    def __init__(self, max_size: int = 4):
        self.max_size = max_size
        self._models: OrderedDict[str, object] = OrderedDict()
        self._lock = RLock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, path: Path):
        import torch
        from transformers import AutoModelForSequenceClassification

        key = str(path.resolve())
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        with self._lock:
            model = self._models.pop(key, None)
            if model is not None:
                self.hits += 1
                self._models[key] = model
                return model, device

            self.misses += 1
            model = AutoModelForSequenceClassification.from_pretrained(
                path,
                local_files_only=True,
            )
            model.to(device).eval()
            self._models[key] = model
            while len(self._models) > self.max_size:
                _, evicted = self._models.popitem(last=False)
                evicted.to("cpu")
                del evicted
                self.evictions += 1
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            return model, device

    def info(self) -> dict:
        with self._lock:
            return {
                "max_size": self.max_size,
                "size": len(self._models),
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "paths": list(self._models),
            }

    def clear(self) -> None:
        import torch

        with self._lock:
            for model in self._models.values():
                model.to("cpu")
            self._models.clear()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


_MODEL_CACHE = _BoundedModelCache(max_size=3)


def model_cache_info() -> dict:
    """Expose cache state for diagnostics without exposing model objects."""
    return _MODEL_CACHE.info()


def _predict_local(
    model_path: Path,
    text: str,
    allowed_labels: list[str] | None = None,
    top_k: int = 3,
) -> dict:
    import torch

    model, device = _MODEL_CACHE.get(model_path)
    tokenizer = _tokenizer()
    encoded = tokenizer(
        [text],
        padding=True,
        truncation=True,
        max_length=128,
        return_tensors="pt",
    )
    with torch.inference_mode():
        probabilities = torch.softmax(
            model(**{key: value.to(device) for key, value in encoded.items()}).logits[0],
            dim=-1,
        ).cpu()
    id_to_label = {
        int(index): label for index, label in model.config.id2label.items()
    }
    if allowed_labels is not None:
        allowed = set(allowed_labels)
        indices = [index for index, label in id_to_label.items() if label in allowed]
        if set(id_to_label[index] for index in indices) != allowed:
            raise ValueError(f"Model labels do not cover routed labels for {model_path}")
        masked = probabilities[indices]
        masked = masked / masked.sum().clamp_min(1e-12)
        ranked = sorted(
            zip(indices, masked.tolist()),
            key=lambda item: item[1],
            reverse=True,
        )
    else:
        ranked = sorted(
            enumerate(probabilities.tolist()),
            key=lambda item: item[1],
            reverse=True,
        )
    best_index, best_confidence = ranked[0]
    return {
        "label": id_to_label[best_index],
        "confidence": float(best_confidence),
        "alternatives": [
            {"label": id_to_label[index], "confidence": float(confidence)}
            for index, confidence in ranked[1:top_k]
        ],
    }


@lru_cache(maxsize=1)
def _names() -> tuple[dict[str, str], dict[str, str]]:
    parents, intents = {}, {}
    for service in load_contract()["services"].values():
        for parent_id, parent in service["parent_topics"].items():
            parents[parent_id] = parent["display_name"]
            for intent_id, intent in parent["query_topics"].items():
                intents[intent_id] = intent["display_name"]
    return parents, intents


@lru_cache(maxsize=1)
def _priority_by_intent() -> dict[str, str]:
    """Load and validate the frozen deterministic intent-to-priority contract."""
    if not PRIORITY_BY_INTENT.exists():
        raise RuntimeError(f"Priority contract is missing: {PRIORITY_BY_INTENT}")
    mapping = json.loads(PRIORITY_BY_INTENT.read_text(encoding="utf-8"))
    if len(mapping) != 264:
        raise ValueError(f"Expected 264 intent priorities, got {len(mapping)}")
    invalid = sorted(set(mapping.values()) - {"Low", "Medium", "High"})
    if invalid:
        raise ValueError(f"Invalid priority labels: {invalid}")
    return {str(intent): str(priority) for intent, priority in mapping.items()}


@dataclass
class LocalUnderstandingPipeline:
    """Production-shaped local pipeline; confidence remains DEV-calibrated only."""

    confidence_threshold: float
    calibration_status: str = "provisional_synthetic_dev_only"

    def predict_understanding(self, text: str, top_k: int = 3) -> dict:
        cleaned = normalize_text(text)
        if not cleaned:
            raise ValueError("text must not be empty")

        # Always retain the XLM-R service score for OOD detection. A unique
        # lexical anchor may override only the routing decision.
        service_model = _predict_local(FINAL / "service", cleaned, top_k=top_k)
        service_model_confidence = float(service_model["confidence"])
        anchor = unique_service_anchor(cleaned)
        if anchor is not None:
            service_id = anchor
            service_confidence = 1.0
            service_routing = "lexical_anchor"
        else:
            service_id = service_model["label"]
            service_confidence = service_model_confidence
            service_routing = "xlm_roberta_fallback"

        parent_labels = list(conditioned_label_map("parent", service_id))
        parent = _predict_local(
            FINAL / "parent" / service_id,
            cleaned,
            allowed_labels=parent_labels,
            top_k=top_k,
        )
        parent_id = parent["label"]

        deterministic_intent = only_intent(service_id, parent_id)
        if deterministic_intent:
            intent = {
                "label": deterministic_intent,
                "confidence": 1.0,
                "alternatives": [],
                "routing": "deterministic_single_leaf",
            }
        else:
            intent_labels = list(conditioned_label_map("intent", service_id, parent_id))
            intent = _predict_local(
                FINAL / "intent" / service_id,
                contextualize_intent_text(cleaned, service_id, parent_id),
                allowed_labels=intent_labels,
                top_k=top_k,
            )
            intent["routing"] = "service_model_parent_masked"

        intent_id = intent["label"]
        priority_map = _priority_by_intent()
        if intent_id not in priority_map:
            raise ValueError(f"Intent missing from priority contract: {intent_id}")
        priority = priority_map[intent_id]
        priority_confidence = 1.0

        # Match the frozen DEV-calibrated OOD policy. Unique non-TAX service
        # anchors are trusted for OOD confidence; TAX anchors and unanchored
        # queries retain the XLM-R service-model maximum-softmax confidence.
        trusted_anchor_for_ood = anchor is not None and anchor != "TAX"
        ood_confidence = 1.0 if trusted_anchor_for_ood else service_model_confidence
        ood_score = 1.0 - ood_confidence
        is_ood = ood_confidence < self.confidence_threshold

        parent_names, intent_names = _names()
        component_confidences = [
            service_confidence,
            float(parent["confidence"]),
            float(intent["confidence"]),
            priority_confidence,
        ]
        warnings = [
            "Confidence/OOD calibration is provisional and based on synthetic DEV data."
        ]
        if is_ood:
            warnings.append("Final OOD routing confidence is below the provisional DEV threshold.")

        return {
            "text": cleaned,
            "service": service_id,
            "service_confidence": service_confidence,
            "service_routing": service_routing,
            "service_anchor": anchor,
            "service_model_label": service_model["label"],
            "service_model_confidence": service_model_confidence,
            "parent_topic_id": parent_id,
            "parent_topic": parent_names[parent_id],
            "parent_confidence": float(parent["confidence"]),
            "query_topic_id": intent_id,
            "query_topic": intent_names[intent_id],
            "intent_confidence": float(intent["confidence"]),
            "intent_routing": intent["routing"],
            "priority": priority,
            "priority_confidence": priority_confidence,
            "priority_routing": "deterministic_from_intent",
            "is_ood": is_ood,
            "ood_score": ood_score,
            "overall_confidence": min(component_confidences),
            "calibration_status": self.calibration_status,
            "warnings": warnings,
            "alternatives": {
                "service": service_model["alternatives"],
                "parent": parent["alternatives"],
                "intent": intent["alternatives"],
                "priority": [],
            },
        }


@lru_cache(maxsize=1)
def load_default_pipeline() -> LocalUnderstandingPipeline:
    """Load the provisional DEV calibration once; models are cached separately."""
    if not CALIBRATION.exists():
        raise RuntimeError(
            "OOD calibration is missing. Run python -m src.models.calibrate_ood first."
        )
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    return LocalUnderstandingPipeline(
        confidence_threshold=float(calibration["confidence_threshold"]),
        calibration_status=str(calibration["calibration_status"]),
    )


def predict_understanding(
    text: str,
    pipeline: UnderstandingPipeline | LocalUnderstandingPipeline | None = None,
) -> dict:
    """Return Partner A's structured understanding result for one query."""
    selected = pipeline if pipeline is not None else load_default_pipeline()
    return selected.predict_understanding(text)
