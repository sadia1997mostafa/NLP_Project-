"""Combine privacy detection with Prothom's frozen classifier output."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from src.models.inference import FINAL, predict_understanding
from src.privacy.detection import detect_privacy
from src.retrieval.lookup import GuidanceLookup
from src.response.controller import construct_response


class ModelUnavailableError(RuntimeError):
    pass


def model_ready() -> bool:
    required = [FINAL / "tokenizer_xlm_roberta_base", FINAL / "service" / "model.safetensors"]
    required += [FINAL / task / service / "model.safetensors" for task in ("parent", "intent") for service in (
        "NID", "BIRTH_REGISTRATION", "PASSPORT", "TAX", "POLICE_GD", "DRIVING_LICENCE"
    )]
    return all(path.exists() for path in required)


class QueryPipeline:
    def __init__(
        self,
        predictor: Callable[[str], dict] = predict_understanding,
        lookup: GuidanceLookup | None = None,
    ):
        self.predictor = predictor
        self.lookup = lookup or GuidanceLookup()
        self._predictor_lock = Lock()

    def analyze(self, text: str) -> dict:
        privacy = detect_privacy(text)
        # The original text is kept in memory only for this classifier call.
        with self._predictor_lock:
            understanding = dict(self.predictor(text))
        understanding["text"] = privacy.safe_text
        retrieval = self.lookup.retrieve(understanding)
        response = construct_response(understanding, retrieval, privacy.warnings)
        # Do not leak an unconfirmed record as an authoritative alternate answer.
        public_retrieval = {**retrieval, "record": None}
        return {
            "privacy_present": privacy.privacy_present,
            "privacy_types": privacy.privacy_types,
            "safe_text": privacy.safe_text,
            "warnings": privacy.warnings,
            "understanding": understanding,
            "retrieval": public_retrieval,
            "response": response,
        }

    def guidance_catalog(self) -> list[dict]:
        return [
            {key: record[key] for key in ("service", "parent_topic_id", "query_topic_id", "title")}
            for record in self.lookup.records
        ]

    def selected_guidance(self, service: str, parent: str | None, topic: str | None) -> dict:
        # Explicit selection must resolve this precise record, never a fallback.
        record = self.lookup.by_key.get((service, parent, topic))
        if record is None:
            raise KeyError("Unknown guidance selection")
        level = "query_topic" if topic else "parent_topic" if parent else "service"
        understanding = {
            "service": service, "parent_topic_id": parent, "query_topic_id": topic,
            "query_topic": record["title"] if topic else None,
            "service_routing": "user_selected", "priority": None, "is_ood": False,
        }
        retrieval = {"status": "found", "match_level": level, "record": record}
        return {
            "privacy_present": False, "privacy_types": [], "safe_text": "", "warnings": [],
            "understanding": understanding, "retrieval": retrieval,
            "response": construct_response(understanding, retrieval, [], confirmed=True),
        }
