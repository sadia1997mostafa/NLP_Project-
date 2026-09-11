"""Checkpoint-agnostic Partner A predict_understanding() contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.preprocessing.text_normalization import normalize_text


class Predictor(Protocol):
    def predict(self, text: str, top_k: int = 3) -> dict: ...


@dataclass
class UnderstandingPipeline:
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
        max_confidence = max(float(outputs["service"]["confidence"]), 0.0)
        ood_score = 1.0 - max_confidence
        rejected = (
            self.confidence_threshold is not None
            and max_confidence < self.confidence_threshold
        ) or (
            self.ood_threshold is not None and ood_score >= self.ood_threshold
        )
        return {
            "service": outputs["service"]["label"],
            "service_confidence": float(outputs["service"]["confidence"]),
            "parent_topic_id": outputs["parent"]["label"],
            "parent_confidence": float(outputs["parent"]["confidence"]),
            "query_topic_id": outputs["intent"]["label"],
            "query_topic_confidence": float(outputs["intent"]["confidence"]),
            "priority": outputs["priority"]["label"],
            "priority_confidence": float(outputs["priority"]["confidence"]),
            "is_ood": rejected,
            "ood_score": ood_score,
            "alternatives": {key: value.get("alternatives", []) for key, value in outputs.items()},
        }


def predict_understanding(text: str, pipeline: UnderstandingPipeline | None = None) -> dict:
    if pipeline is None:
        raise RuntimeError(
            "No trained checkpoints are configured. Inject an UnderstandingPipeline "
            "after the four classifiers have been trained and calibrated."
        )
    return pipeline.predict_understanding(text)
