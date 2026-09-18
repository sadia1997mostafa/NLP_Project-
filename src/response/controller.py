"""Build display content only from verified corpus records and fixed fallbacks."""

from __future__ import annotations


def construct_response(understanding: dict, retrieval: dict, privacy_warnings: list[str]) -> dict:
    base = {
        "priority": understanding.get("priority"),
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
    # More corpus coverage is not evidence that an unanchored prediction is correct.
    if understanding.get("service_routing") == "xlm_roberta_fallback":
        return {
            **base,
            "state": "clarification",
            "title": "Please confirm the service",
            "body": "Please name the government service and your specific question so I can confirm the intended service.",
            "scope_note": None,
        }
    record = retrieval["record"]
    return {
        **base,
        "state": "answer",
        "title": record["title"],
        "body": record["guidance"],
        "scope_note": (
            "This is general guidance. Verified instructions for the specific topic are not available here."
            if retrieval["match_level"] != "query_topic" else None
        ),
        "required_documents": record["required_documents"],
        "source": {
            "name": record["official_source"],
            "url": record["source_url"],
            "last_verified": record["last_verified"],
        },
    }
