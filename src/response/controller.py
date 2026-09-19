"""Build display content only from verified corpus records and fixed fallbacks."""

from __future__ import annotations

import re

from src.response.facts import facts_for, render_fact


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
        "answer_basis": None,
        "answer_type": None,
        "grounding_level": None,
        "clarification_question": None,
        "plan_warnings": [],
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
    plan = record.get("answer_plan")
    if plan is not None:
        direct = plan["direct_answer"][language]
        question = (
            plan["clarification_question"][language]
            if plan["clarification_question"] is not None else None
        )
        state = "clarification" if plan["grounding_level"] == "SAFE_CLARIFICATION" else "answer"
        if state == "clarification" and question:
            direct = f"{direct} {question}"
        steps = [item[language] for item in plan["steps"]]
        if state == "answer" and plan["grounding_level"] == "VERIFIED_GENERAL" and question:
            steps.append(question)
        return {
            **base,
            "state": state,
            "title": plan["title"],
            "body": direct,
            "steps": steps,
            "required_documents": plan["required_documents"],
            "answer_basis": "exact_intent_answer_plan",
            "answer_type": plan["answer_type"],
            "grounding_level": plan["grounding_level"],
            "clarification_question": question,
            "plan_warnings": [item[language] for item in plan["warnings"]],
            "scope_note": plan["scope_note"][language],
            "source": {
                "name": plan["official_source"],
                "url": plan["source_url"],
                "last_verified": plan["last_verified"],
            },
        }
    units = facts_for(record)
    lead = [unit for unit in units[1:] if unit.get("prominence") == "lead"]
    steps = [unit for unit in units[1:] if unit.get("prominence") != "lead"]
    return {
        **base,
        "state": "answer",
        "title": record["title"],
        "body": " ".join(render_fact(unit, language) for unit in [units[0], *lead]),
        "steps": [render_fact(unit, language) for unit in steps],
        "answer_basis": "curated_source_facts",
        "language_note": (
            "নথির নাম ও শর্তগুলো উৎস অনুযায়ী ইংরেজিতে দেখানো হয়েছে।"
            if bengali and record["required_documents"] else None
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
