"""Build display content only from verified corpus records and fixed fallbacks."""

from __future__ import annotations

import re


def response_language(text: str) -> str:
    if any("\u0980" <= char <= "\u09ff" for char in text):
        return "bn"
    return "bn" if re.search(r"\b(?:amar|kivabe|korbo|lagbe|ki|chai)\b", text.lower()) else "en"


def construct_response(
    understanding: dict, retrieval: dict, privacy_warnings: list[str], *, confirmed: bool = False,
) -> dict:
    language = understanding.get("response_language") or response_language(understanding.get("text", ""))
    bengali = language == "bn"
    base = {
        "language": language,
        "priority": understanding.get("priority") if confirmed else None,
        "privacy_warnings": privacy_warnings,
        "match_level": retrieval["match_level"],
        "source": None,
        "required_documents": [],
        "steps": [],
        "language_note": None,
    }
    if retrieval["status"] == "ood":
        return {
            **base,
            "state": "clarification",
            "title": "অনুরোধটি স্পষ্ট করুন" if bengali else "Please clarify your request",
            "body": (
                "সমর্থিত সরকারি সেবাটি নিশ্চিত হতে পারিনি। সেবার নাম ও কী করতে চান লিখুন।"
                if bengali else
                "I could not reliably identify a supported government service. Please mention the service and what you need to do."
            ),
            "scope_note": None,
        }
    if retrieval["status"] == "miss":
        return {
            **base,
            "state": "unavailable",
            "title": "যাচাইকৃত নির্দেশনা পাওয়া যায়নি" if bengali else "Verified guidance unavailable",
            "body": (
                "এই বিষয়ে এখনো যাচাইকৃত নির্দেশনা নেই। সংশ্লিষ্ট সরকারি সেবার মূল সাইট দেখুন।"
                if bengali else
                "I do not have verified guidance for this request yet. Please consult the relevant official government service."
            ),
            "scope_note": None,
        }
    # Service anchors and exact retrieval do not establish correct intent classification.
    if not confirmed:
        return {
            **base,
            "state": "clarification",
            "title": "কোন বিষয়টি জানতে চান?" if bengali else "Which topic did you mean?",
            "body": "আপনার প্রশ্নের নির্দিষ্ট বিষয়টি নিশ্চিত হতে পারিনি।" if bengali else "I could not reliably confirm the topic of your question.",
            "scope_note": None,
        }
    record = retrieval["record"]
    specific = retrieval["match_level"] == "query_topic"
    steps = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", record["guidance"]) if sentence.strip()]
    if bengali:
        body = (
            "আপনার প্রশ্নের বিষয়ে যাচাইকৃত তথ্য নিচে দেওয়া আছে। বর্তমান নিয়ম মূল সরকারি সাইটে মিলিয়ে নিন।"
            if specific else
            "সেবাটি শনাক্ত হয়েছে, কিন্তু নির্দিষ্ট উপবিষয় নিশ্চিত নয়। এটি সাধারণ নির্দেশনা; বিস্তারিত জানতে বিষয় বেছে নিন।"
        )
    else:
        body = (
            f"For {record['title'].lower()}, follow the verified guidance below. "
            "Check the official source for current requirements."
            if specific else
            "I identified the service, but not the exact topic reliably. "
            "This is general guidance; choose a topic for a more specific answer."
        )
    if record["query_topic_id"] == "POLICE_GD_EMERGENCY_ROUTING":
        body = (
            "জরুরি বিপদে বাংলাদেশে ৯৯৯-এ কল করুন। এই অ্যাপ সাহায্য পাঠাতে পারে না; অনলাইন জিডির জন্য অপেক্ষা করবেন না।"
            if bengali else
            "If there is immediate danger in Bangladesh, call 999 now. This app cannot dispatch help; do not wait for an online GD."
        )
    return {
        **base,
        "state": "answer",
        "title": record["title"],
        "body": body,
        "steps": steps,
        "language_note": (
            "মূল উৎস থেকে যাচাইকৃত বিস্তারিত তথ্য নিচে ইংরেজিতে আছে।"
            if bengali and record["language"] == "en" else None
        ),
        "scope_note": (
            ("এটি নির্বাচিত বিষয়ের সাধারণ নির্দেশনা।" if bengali else "This is general guidance for the selected topic.")
            if retrieval["match_level"] == "parent_topic"
            else ("এটি সেবার সারসংক্ষেপ, নির্দিষ্ট প্রক্রিয়া নয়।" if bengali else "This is a service overview, not a specific procedure.")
            if retrieval["match_level"] == "service" else None
        ),
        "required_documents": record["required_documents"],
        "source": {
            "name": record["official_source"],
            "url": record["source_url"],
            "last_verified": record["last_verified"],
        },
    }
