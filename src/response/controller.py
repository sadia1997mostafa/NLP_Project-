"""Build display content only from verified corpus records and fixed fallbacks."""

from __future__ import annotations


def construct_response(
    understanding: dict, retrieval: dict, privacy_warnings: list[str], *, confirmed: bool = False,
) -> dict:
    base = {
        "priority": understanding.get("priority") if confirmed else None,
        "privacy_warnings": privacy_warnings,
        "match_level": retrieval["match_level"],
        "source": None,
        "required_documents": [],
    }
    if retrieval["status"] == "ood":
        return {
            **base,
            "state": "clarification",
            "title": "Please clarify your request",
            "body": "I could not reliably identify a supported government service. Please mention the service and what you need to do.",
            "scope_note": None,
        }
    if retrieval["status"] == "miss":
        return {
            **base,
            "state": "unavailable",
            "title": "Verified guidance unavailable",
            "body": "I do not have verified guidance for this request yet. Please consult the relevant official government service.",
            "scope_note": None,
        }
    # Service anchors and exact retrieval do not establish correct intent classification.
    if not confirmed:
        return {
            **base,
            "state": "clarification",
            "title": "Which topic did you mean?",
            "body": "I could not reliably confirm the topic of your question.",
            "scope_note": None,
        }
    record = retrieval["record"]
    return {
        **base,
        "state": "answer",
        "title": record["title"],
        "body": record["guidance"],
        "scope_note": (
            "This is general guidance for the selected topic."
            if retrieval["match_level"] == "parent_topic"
            else "This is a service overview, not a specific procedure."
            if retrieval["match_level"] == "service" else None
        ),
        "required_documents": record["required_documents"],
        "source": {
            "name": record["official_source"],
            "url": record["source_url"],
            "last_verified": record["last_verified"],
        },
    }
