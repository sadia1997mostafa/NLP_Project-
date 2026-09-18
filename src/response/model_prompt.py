"""Shared prompt contract for local answer-model training and inference."""

from __future__ import annotations

import json


BASE_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
SYSTEM_PROMPT = (
    "You are a Bangladesh public-service guidance writer. Answer the user's "
    "specific question using only the approved record provided. Write naturally "
    "and concisely in the requested language. Preserve conditions and warnings. "
    "Do not invent fees, deadlines, eligibility, documents, or outcomes. "
    "Do not repeat personal identifiers. Do not add links; the app shows the "
    "official source separately. If the record does not answer the question, "
    "say that verified guidance is unavailable for that detail."
)


def prompt_messages(question: str, record: dict, language: str) -> list[dict[str, str]]:
    if language not in {"en", "bn"}:
        raise ValueError("Unsupported answer language")
    payload = {
        "question": question,
        "language": "Bengali" if language == "bn" else "English",
        "service": record["service"],
        "topic": record["title"],
        "approved_guidance": record["guidance"],
        "document_conditions": record["required_documents"],
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
