"""Combine privacy detection with Prothom's frozen classifier output."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from src.models.inference import FINAL, predict_understanding
from src.pipeline.service_evidence import evidenced_services
from src.privacy.detection import detect_privacy
from src.retrieval.lookup import GuidanceLookup
from src.retrieval.topic_match import match_parent, match_topic
from src.response.controller import construct_response, response_language
from src.response.local_generator import LocalAnswerGenerator, acceptable_answer, configured_model_path, local_generator_ready


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
        answer_generator: LocalAnswerGenerator | None = None,
    ):
        self.predictor = predictor
        self.lookup = lookup or GuidanceLookup()
        self._predictor_lock = Lock()
        model_path = configured_model_path()
        self.answer_generator = answer_generator or (
            LocalAnswerGenerator(model_path) if local_generator_ready() and model_path else None
        )

    def analyze(self, text: str) -> dict:
        privacy = detect_privacy(text)
        # The original text is kept in memory only for this classifier call.
        with self._predictor_lock:
            understanding = dict(self.predictor(text))
        understanding["text"] = privacy.safe_text
        language = response_language(privacy.safe_text)
        understanding["response_language"] = language
        privacy_warnings = (
            ["ব্যক্তিগত তথ্য পাওয়া গেছে। সরকারি সেবায় প্রয়োজন না হলে পরিচয় নম্বর বা গোপন কোড শেয়ার করবেন না।"]
            if privacy.privacy_present and language == "bn" else privacy.warnings
        )
        evidence = evidenced_services(privacy.safe_text)
        if len(evidence) == 1:
            resolved_service = next(iter(evidence))
            if resolved_service != understanding.get("service"):
                understanding["model_service"] = understanding.get("service")
                understanding["model_parent_topic_id"] = understanding.get("parent_topic_id")
                understanding["model_query_topic_id"] = understanding.get("query_topic_id")
                understanding["service"] = resolved_service
                understanding["parent_topic_id"] = None
                understanding["query_topic_id"] = None
                understanding["priority"] = None
                understanding["service_resolution"] = "explicit_name_correction"
        retrieval = self.lookup.retrieve(understanding)
        effective = dict(understanding)
        if len(evidence) != 1:
            retrieval = {"status": "ood", "match_level": None, "record": None}
        elif retrieval["status"] != "ood":
            match = match_topic(
                privacy.safe_text, understanding.get("service"),
                understanding.get("query_topic_id"), self.lookup.records,
            )
            if match.record is not None:
                record = match.record
                retrieval = {"status": "found", "match_level": "query_topic", "record": record}
                effective["parent_topic_id"] = record["parent_topic_id"]
                effective["query_topic_id"] = record["query_topic_id"]
                if record["query_topic_id"] != understanding.get("query_topic_id"):
                    effective["priority"] = None
                understanding["resolved_topic_id"] = record["query_topic_id"]
                understanding["topic_resolution"] = "corpus_similarity"
            else:
                parent = match_parent(
                    privacy.safe_text, understanding.get("service"),
                    understanding.get("parent_topic_id"), self.lookup.records,
                )
                if parent.record is not None:
                    record = parent.record
                    retrieval = {"status": "found", "match_level": "parent_topic", "record": record}
                    understanding["resolved_parent_id"] = record["parent_topic_id"]
                else:
                    record = self.lookup.by_key.get((understanding.get("service"), None, None))
                    retrieval = (
                        {"status": "found", "match_level": "service", "record": record}
                        if record is not None else {"status": "miss", "match_level": None, "record": None}
                    )
                effective["priority"] = None
                understanding["topic_resolution"] = "unconfirmed"
        response = construct_response(effective, retrieval, privacy_warnings, confirmed=True)
        if (self.answer_generator is not None and response["state"] == "answer"
                and retrieval["match_level"] == "query_topic"
                and retrieval["record"]["query_topic_id"] != "POLICE_GD_EMERGENCY_ROUTING"):
            try:
                generated = self.answer_generator.generate(privacy.safe_text, retrieval["record"], language)
                if acceptable_answer(generated, retrieval["record"], language):
                    response["body"] = generated
                    response["steps"] = []
                    response["answer_basis"] = "local_finetuned_model"
                    response["scope_note"] = (
                        "এটি মডেল-লেখা সারাংশ; সরকারি উৎসের সঙ্গে তথ্য মিলিয়ে নিন।" if language == "bn"
                        else "This is a model-written summary; verify details with the official source."
                    )
            except Exception:
                # A missing or failing optional model must not suppress verified guidance.
                pass
        # Do not leak an unconfirmed record as an authoritative alternate answer.
        public_retrieval = {**retrieval, "record": None}
        return {
            "privacy_present": privacy.privacy_present,
            "privacy_types": privacy.privacy_types,
            "safe_text": privacy.safe_text,
            "warnings": privacy_warnings,
            "understanding": understanding,
            "retrieval": public_retrieval,
            "response": response,
        }

    def guidance_catalog(self) -> list[dict]:
        return [
            {key: record[key] for key in ("service", "parent_topic_id", "query_topic_id", "title")}
            for record in self.lookup.records
        ]

    def selected_guidance(self, service: str, parent: str | None, topic: str | None, language: str = "en") -> dict:
        # Explicit selection must resolve this precise record, never a fallback.
        record = self.lookup.by_key.get((service, parent, topic))
        if record is None:
            raise KeyError("Unknown guidance selection")
        level = "query_topic" if topic else "parent_topic" if parent else "service"
        understanding = {
            "service": service, "parent_topic_id": parent, "query_topic_id": topic,
            "query_topic": record["title"] if topic else None,
            "service_routing": "user_selected", "priority": None, "is_ood": False,
            "response_language": language,
        }
        retrieval = {"status": "found", "match_level": level, "record": record}
        return {
            "privacy_present": False, "privacy_types": [], "safe_text": "", "warnings": [],
            "understanding": understanding, "retrieval": retrieval,
            "response": construct_response(understanding, retrieval, [], confirmed=True),
        }
