"""Conservative corpus-side intent check; the frozen classifier is unchanged."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass(frozen=True)
class TopicMatch:
    record: dict | None
    score: float
    margin: float


GENERIC_WORDS = {
    "a", "an", "and", "about", "can", "could", "do", "for", "get", "help", "how",
    "i", "in", "is", "ki", "kivabe", "korbo", "my", "need", "online", "please",
    "the", "to", "want", "what", "where", "with", "জন্য", "কিভাবে", "কীভাবে", "আমি",
    "আমার", "অনলাইন", "সাহায্য", "করব", "করবো",
}
SERVICE_WORDS = {
    "nid", "national", "id", "birth", "registration", "certificate", "passport",
    "tax", "tin", "gd", "police", "driving", "licence", "license", "learner", "brta",
    "এনআইডি", "জাতীয়", "পরিচয়পত্র", "জন্ম", "নিবন্ধন", "সনদ", "পাসপোর্ট",
    "আয়কর", "ট্যাক্স", "জিডি", "ড্রাইভিং", "লাইসেন্স",
}


def _has_topic_signal(text: str) -> bool:
    words = re.findall(r"[^\W\d_]+", text.lower(), flags=re.UNICODE)
    return any(len(word) >= 4 and word not in GENERIC_WORDS | SERVICE_WORDS for word in words)


def match_topic(text: str, service: str, predicted_topic: str | None, records: list[dict]) -> TopicMatch:
    candidates = [
        record for record in records
        if record["service"] == service and record["query_topic_id"] is not None
    ]
    if not candidates or not _has_topic_signal(text):
        return TopicMatch(None, 0.0, 0.0)
    descriptions = [
        f"{record['title']} {record['query_topic_id'].replace('_', ' ')}"
        for record in candidates
    ]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    matrix = vectorizer.fit_transform([*descriptions, text])
    scores = (matrix[:-1] @ matrix[-1].T).toarray().ravel()
    ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    best, runner_up = ranked[0], ranked[1] if len(ranked) > 1 else None
    score = float(scores[best])
    margin = score - (float(scores[runner_up]) if runner_up is not None else 0.0)
    agrees = candidates[best]["query_topic_id"] == predicted_topic
    # These gates are for answer display, not changes to Prothom's model/OOD policy.
    accepted = (score >= 0.28 and margin >= 0.06) or (agrees and score >= 0.32)
    return TopicMatch(candidates[best] if accepted else None, score, margin)
