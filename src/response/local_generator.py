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


MODEL_ENV = "NAGORIKSHEBA_ANSWER_GGUF"


def configured_model_path() -> Path | None:
    value = os.environ.get(MODEL_ENV, "").strip()
    return Path(value).expanduser() if value else None


def local_generator_ready() -> bool:
    path = configured_model_path()
    return bool(path and path.is_file() and find_spec("llama_cpp") is not None)


def _digits(text: str) -> set[str]:
    normalized = "".join(str(unicodedata.digit(char)) if char.isdecimal() else char for char in text)
    return set(re.findall(r"\d+", normalized))


def acceptable_answer(answer: str, record: dict, language: str) -> bool:
    if not isinstance(answer, str):
        return False
    answer = answer.strip()
    if (not 20 <= len(answer) <= 800 or "<|" in answer
            or re.search(r"\[(?:NID|OTP|PHONE|PASSWORD|EMAIL|ADDRESS|NAME|PASSPORT|DATE_OF_BIRTH)\]", answer)):
        return False
    if re.search(r"https?://|www\.", answer, re.I) or detect_privacy(answer).privacy_present:
        return False
    if language == "bn" and len(re.findall(r"[\u0980-\u09ff]", answer)) < 10:
        return False
    if language == "en" and len(re.findall(r"[\u0980-\u09ff]", answer)) >= 10:
        return False
    approved = " ".join([record["guidance"], *record["required_documents"]])
    if not _digits(answer) <= _digits(approved):
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
                temperature=0.1, max_tokens=220,
            )
        return result["choices"][0]["message"]["content"].strip()
