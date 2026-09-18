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
        return {
            "privacy_present": privacy.privacy_present,
            "privacy_types": privacy.privacy_types,
            "safe_text": privacy.safe_text,
            "warnings": privacy.warnings,
            "understanding": understanding,
            "retrieval": retrieval,
            "response": construct_response(understanding, retrieval, privacy.warnings),
        }
