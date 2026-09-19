"""Optional in-process GGUF answer writer; no hosted inference or API calls."""

from __future__ import annotations

import os
import re
import unicodedata
from importlib.util import find_spec
from pathlib import Path
from threading import Lock

from src.privacy.detection import detect_privacy
from src.response.model_prompt import prompt_messages
from src.response.plans import approved_plan_texts


MODEL_ENV = "NAGORIKSHEBA_ANSWER_GGUF"
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "answer_generator"
FOREIGN_SCRIPT = re.compile(
    r"[\u0400-\u052f\u0600-\u06ff\u0750-\u077f\u0900-\u0963\u0966-\u097f"
    r"\u0e00-\u0e7f\u1100-\u11ff\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]"
)
DOMAIN = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:bd|com|org|net|gov|edu|io|co)(?:\.[a-z]{2})?\b", re.I,
)
COMMON_WORDS = {
    "a", "an", "and", "are", "for", "in", "is", "of", "on", "or", "the", "this", "to", "your",
    "এই", "এবং", "এর", "ও", "করুন", "জন্য",
}
SENSITIVE_CLAIM_GROUPS = (
    ("fee", "fees", "cost", "free", "টাকা", "ফি"),
    ("deadline", "day", "days", "week", "weeks", "month", "months", "সপ্তাহ", "মাস"),
    ("eligible", "eligibility", "ineligible", "যোগ্য", "অযোগ্য"),
    ("required", "mandatory", "must", "অবশ্যই", "বাধ্যতামূলক"),
    ("guarantee", "guaranteed", "approve", "approved", "accepted", "successful", "completed", "refund", "deliver", "delivered", "arrive", "done", "নিশ্চিত", "অনুমোদন", "গৃহীত", "সফল", "সম্পন্ন", "ফেরত", "হয়ে যাবে", "চলে যাবে"),
)


def _contains_claim(text: str, term: str) -> bool:
    if term.isascii():
        return bool(re.search(rf"\b{re.escape(term)}\b", text, re.I))
    return term in text


def configured_model_path() -> Path | None:
    value = os.environ.get(MODEL_ENV, "").strip()
    if value:
        return Path(value).expanduser()

    candidates = sorted(DEFAULT_MODEL_DIR.glob("*.gguf"))
    return candidates[0] if len(candidates) == 1 else None


def local_generator_ready() -> bool:
    path = configured_model_path()
    return bool(path and path.is_file() and find_spec("llama_cpp") is not None)


def _digits(text: str) -> set[str]:
    normalized = "".join(str(unicodedata.digit(char)) if char.isdecimal() else char for char in text)
    return set(re.findall(r"\d+", normalized))


def _has_repeated_phrase(text: str) -> bool:
    words = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
    if len(words) < 12:
        return False
    phrases = [tuple(words[index:index + 4]) for index in range(len(words) - 3)]
    return any(phrases.count(phrase) >= 3 for phrase in set(phrases))


def _content_tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
        if len(token) > 1 and token not in COMMON_WORDS
    }


def acceptable_answer(
    answer: str,
    record: dict,
    language: str,
    question: str | None = None,
) -> bool:
    if not isinstance(answer, str):
        return False
    answer = answer.strip()
    if (not 20 <= len(answer) <= 800 or "<|" in answer or "\ufffd" in answer
            or re.search(r"<[^>]*>", answer)
            or re.match(r"(?i)\s*(?:language\s*:|limburg\b|taboola\b)", answer)
            or re.search(r"\[[A-Z][A-Z0-9_]{1,40}\]", answer)):
        return False
    if (re.search(r"https?://|www\.", answer, re.I) or DOMAIN.search(answer)
            or FOREIGN_SCRIPT.search(answer) or _has_repeated_phrase(answer)
            or detect_privacy(answer).privacy_present):
        return False
    if language == "bn":
        question_has_bangla = bool(question and re.search(r"[\u0980-\u09ff]", question))
        if question_has_bangla and len(re.findall(r"[\u0980-\u09ff]", answer)) < 10:
            return False
    if language == "en" and len(re.findall(r"[\u0980-\u09ff]", answer)) >= 10:
        return False
    approved_facts = approved_plan_texts(record, language)
    if not approved_facts:
        return False
    approved = " ".join([record["guidance"], *record["required_documents"], *approved_facts])
    if not _digits(answer) <= _digits(approved):
        return False
    answer_folded = answer.casefold()
    approved_folded = approved.casefold()
    for group in SENSITIVE_CLAIM_GROUPS:
        if any(_contains_claim(answer_folded, term) for term in group) and not any(
            _contains_claim(approved_folded, term) for term in group
        ):
            return False
    answer_tokens = _content_tokens(answer)
    grounded_count = len(answer_tokens & _content_tokens(" ".join(approved_facts)))
    if grounded_count < 2 or grounded_count / max(1, len(answer_tokens)) < 0.2:
        return False
    if answer == record["guidance"].strip():
        return False
    return True


class LocalAnswerGenerator:
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self._model = None
        self._lock = Lock()

    def generate(self, question: str, record: dict, language: str) -> str:
        with self._lock:
            if self._model is None:
                from llama_cpp import Llama

                self._model = Llama(
                    model_path=str(self.model_path), n_ctx=2048, n_threads=max(1, (os.cpu_count() or 2) // 2),
                    verbose=False,
                )
            result = self._model.create_chat_completion(
                messages=prompt_messages(question, record, language),
                temperature=0.45,
                top_p=0.9,
                repeat_penalty=1.08,
                max_tokens=512,
            )
        return result["choices"][0]["message"]["content"].strip()
