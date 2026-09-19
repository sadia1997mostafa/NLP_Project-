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
    "a", "an", "and", "about", "can", "check", "could", "do", "for", "get", "help", "how",
    "i", "in", "is", "ki", "kivabe", "korbo", "my", "need", "online", "please",
    "amar", "hoye", "geche", "change",
    "the", "to", "want", "what", "where", "with", "koto", "জন্য", "কিভাবে", "কীভাবে", "আমি",
    "আমার", "অনলাইন", "সাহায্য", "করব", "করবো",
    "করতে", "করে", "পারি", "লাগবে", "দেব",
}
SERVICE_WORDS = {
    "nid", "national", "id", "birth", "registration", "certificate", "passport",
    "tax", "tin", "gd", "police", "driving", "licence", "license", "learner", "brta",
    "এনআইডি", "জাতীয়", "পরিচয়পত্র", "জন্ম", "নিবন্ধন", "সনদ", "পাসপোর্ট",
    "আয়কর", "ট্যাক্স", "জিডি", "ড্রাইভিং", "লাইসেন্স",
}
BENGALI_HINTS = {
    "আবেদন": "apply apply application", "যাচাই": "verification verify record",
    "কাগজপত্র": "documents", "নথি": "documents", "সংশোধন": "correction correct",
    "স্ট্যাটাস": "status track", "অবস্থা": "status track", "জমা": "submission submit",
    "রিটার্ন": "return", "ফি": "fee", "নবায়ন": "renewal", "ফলাফল": "result",
    "হারিয়ে": "lost replacement", "হারানো": "lost replacement",
    "জন্ম তারিখ": "date of birth dob", "পাসপোর্ট": "passport",
    "জন্ম নিবন্ধন": "birth registration", "ড্রাইভিং লাইসেন্স": "driving licence",
    "এনআইডি": "nid", "জিডি": "gd", "ট্যাক্স": "tax", "জরুরি": "emergency urgent",
}
QUALIFIERS = {
    "LEARNER": ("learner", "লার্নার", "শিক্ষানবিশ"),
    "MINOR": ("child", "minor", "শিশু", "অপ্রাপ্তবয়স্ক"),
    "DOB": ("date of birth", "dob", "জন্ম তারিখ"),
    "ADDRESS": ("address", "ঠিকানা"),
    "BLOOD_GROUP": ("blood", "রক্ত"),
    "OTP": ("otp", "ওটিপি"),
}
FOCUS_TERMS = {
    "status", "fee", "document", "verification", "verify", "renewal", "duplicate",
    "correction", "emergency", "urgent",
}


def _content_tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    singular = {"fees": "fee", "documents": "document", "requirements": "requirement", "forms": "form"}
    return [
        singular.get(word, word) for word in words
        if len(word) >= 3 and word not in GENERIC_WORDS | SERVICE_WORDS | {"services", "br"}
    ]


def _qualifier_supported(record: dict, text: str) -> bool:
    topic_id = record["query_topic_id"] or record["parent_topic_id"]
    lowered = text.lower()
    if "OTHER_INCIDENT" in topic_id and any(term in lowered for term in ("emergency", "urgent", "জরুরি")):
        return False
    return all(
        not re.search(rf"(?:^|_){qualifier}(?:_|$)", topic_id)
        or any(term in lowered for term in terms)
        for qualifier, terms in QUALIFIERS.items()
    )


def _match(text: str, candidates: list[dict], label_key: str, predicted: str | None) -> TopicMatch:
    expanded = f"{text} {' '.join(english for bangla, english in BENGALI_HINTS.items() if bangla in text)}"
    query_terms = _content_tokens(expanded)
    if not candidates or not query_terms:
        return TopicMatch(None, 0.0, 0.0)
    descriptions = [
        _content_tokens(f"{record['title']} {record[label_key].replace('_', ' ')}")
        for record in candidates
    ]
    focus = set(query_terms) & FOCUS_TERMS
    eligible = [
        index for index, record in enumerate(candidates)
        if _qualifier_supported(record, text) and set(query_terms) & set(descriptions[index])
        and (not focus or focus & set(descriptions[index]))
    ]
    if not eligible:
        return TopicMatch(None, 0.0, 0.0)
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    matrix = vectorizer.fit_transform([*(" ".join(tokens) for tokens in descriptions), " ".join(query_terms)])
    scores = (matrix[:-1] @ matrix[-1].T).toarray().ravel()
    ranked = sorted(
        eligible,
        key=lambda index: scores[index], reverse=True,
    )
    if not ranked:
        return TopicMatch(None, 0.0, 0.0)
    best, runner_up = ranked[0], ranked[1] if len(ranked) > 1 else None
    score = float(scores[best])
    margin = score - (float(scores[runner_up]) if runner_up is not None else 0.0)
    agrees = candidates[best][label_key] == predicted
    # These gates are for answer display, not changes to Prothom's model/OOD policy.
    threshold = 0.25 if focus else 0.28
    accepted = ((score >= threshold and margin >= 0.06) or (agrees and score >= threshold))
    return TopicMatch(candidates[best] if accepted else None, score, margin)


def match_topic(text: str, service: str, predicted_topic: str | None, records: list[dict]) -> TopicMatch:
    candidates = [
        record for record in records
        if record["service"] == service and record["query_topic_id"] is not None
        and (
            "answer_plan" not in record
            or record["answer_plan"]["grounding_level"] == "VERIFIED_SPECIFIC"
        )
    ]
    return _match(text, candidates, "query_topic_id", predicted_topic)


def match_parent(text: str, service: str, predicted_parent: str | None, records: list[dict]) -> TopicMatch:
    candidates = [
        record for record in records
        if record["service"] == service and record["parent_topic_id"] is not None
        and record["query_topic_id"] is None
    ]
    return _match(text, candidates, "parent_topic_id", predicted_parent)
