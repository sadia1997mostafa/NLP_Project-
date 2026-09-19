"""Validated, exact-intent answer plans for safe response realization."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from src.models.hierarchy import load_contract


PLANS_PATH = Path(__file__).resolve().parents[2] / "knowledge_base/answer_plans.json"

_DOCUMENT_LABELS_BN = {
    "Active mobile number": "সচল মোবাইল নম্বর",
    "Applicable deed, utility bill, rental agreement or rent receipt":
        "প্রযোজ্য দলিল, ইউটিলিটি বিল, ভাড়ার চুক্তিপত্র বা ভাড়ার রসিদ",
    "Applicable income, investment, expenditure, asset/liability and tax-payment records":
        "প্রযোজ্য আয়, বিনিয়োগ, ব্যয়, সম্পদ/দায় ও কর পরিশোধের নথি",
    "Applicant photograph": "আবেদনকারীর ছবি",
    "Current-address utility bill if different from NID":
        "NID-এর ঠিকানা আলাদা হলে বর্তমান ঠিকানার ইউটিলিটি বিল",
    "Educational certificate": "শিক্ষাগত সনদ",
    "Evidence for requested corrections, if any":
        "চাওয়া সংশোধনের সমর্থনে প্রমাণপত্র, প্রযোজ্য হলে",
    "For under-six applicants: 3R lab-printed photograph with grey background":
        "ছয় বছরের কম বয়সী আবেদনকারীর জন্য ধূসর পটভূমিতে ল্যাব-প্রিন্ট করা 3R ছবি",
    "GD copy": "GD-এর কপি",
    "GO/NOC for government employment, as applicable":
        "সরকারি চাকরির ক্ষেত্রে প্রযোজ্য GO/NOC",
    "Learner licence": "লার্নার লাইসেন্স",
    "Live photograph": "সরাসরি তোলা ছবি",
    "Medical certificate confirming blood group": "রক্তের গ্রুপ উল্লেখ করা মেডিকেল সনদ",
    "Medical certificate from a registered doctor": "নিবন্ধিত চিকিৎসকের মেডিকেল সনদ",
    "NID information": "NID-এর তথ্য",
    "NID scan": "NID-এর স্ক্যান কপি",
    "Offline-payment receipt, if paid offline": "অফলাইনে পরিশোধ করলে পেমেন্টের রসিদ",
    "Online English birth registration certificate": "অনলাইন ইংরেজি জন্মনিবন্ধন সনদ",
    "Original NID or birth certificate, as applicable": "প্রযোজ্য ক্ষেত্রে মূল NID বা জন্মসনদ",
    "Original previous passport, for reissue": "পুনঃইস্যুর জন্য আগের পাসপোর্টের মূল কপি",
    "Other papers specified for your test": "আপনার পরীক্ষার জন্য নির্ধারিত অন্যান্য কাগজপত্র",
    "Parent's NID information when applicable": "প্রযোজ্য ক্ষেত্রে বাবা-মায়ের NID-এর তথ্য",
    "Photocopy of the previous passport": "আগের পাসপোর্টের ফটোকপি",
    "Previous passport, if any": "আগের পাসপোর্ট, থাকলে",
    "Printed application form and summary, including appointment if any":
        "প্রিন্ট করা আবেদনপত্র ও summary, appointment থাকলে সেটিসহ",
    "SSC/equivalent certificate if applicable; otherwise evidence specified for your category":
        "প্রযোজ্য হলে SSC/সমমানের সনদ; অন্যথায় আপনার শ্রেণির জন্য নির্ধারিত প্রমাণপত্র",
}

GROUNDING_LEVELS = {
    "VERIFIED_SPECIFIC",
    "VERIFIED_GENERAL",
    "SAFE_CLARIFICATION",
}
ANSWER_TYPES = {
    "PROCEDURE",
    "DOCUMENTS",
    "STATUS",
    "ELIGIBILITY",
    "FEE",
    "CORRECTION",
    "REPLACEMENT",
    "TROUBLESHOOTING",
    "VERIFICATION",
    "ACCOUNT_ACCESS",
    "PAYMENT",
    "GENERAL_INFORMATION",
    "EMERGENCY",
    "CLARIFICATION",
}
REQUIRED_FIELDS = {
    "query_topic_id",
    "service",
    "parent_topic_id",
    "title",
    "answer_type",
    "grounding_level",
    "direct_answer",
    "steps",
    "required_documents",
    "warnings",
    "clarification_question",
    "official_source",
    "source_url",
    "last_verified",
    "scope_note",
}


def _localized(value: object, *, optional: bool = False) -> bool:
    if optional and value is None:
        return True
    return (
        isinstance(value, dict)
        and set(value) == {"en", "bn"}
        and all(isinstance(value[language], str) and value[language].strip() for language in ("en", "bn"))
    )


def _official_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.hostname.endswith(".gov.bd")
        and parsed.username is None
        and parsed.password is None
    )


@lru_cache(maxsize=1)
def load_answer_plans(path: Path = PLANS_PATH) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"version", "plans"}:
        raise ValueError("Answer-plan file must contain version and plans")
    if not isinstance(payload["version"], str) or not payload["version"].strip():
        raise ValueError("Answer-plan version is missing")
    if not isinstance(payload["plans"], list):
        raise ValueError("Answer plans must be a list")

    contract = load_contract()
    expected: dict[str, tuple[str, str]] = {}
    for service, service_data in contract["services"].items():
        for parent_id, parent in service_data["parent_topics"].items():
            for topic_id in parent["query_topics"]:
                expected[topic_id] = (service, parent_id)

    plans: dict[str, dict] = {}
    for number, plan in enumerate(payload["plans"], start=1):
        if not isinstance(plan, dict) or set(plan) != REQUIRED_FIELDS:
            raise ValueError(f"Answer plan {number} has invalid fields")
        topic_id = plan["query_topic_id"]
        if topic_id in plans:
            raise ValueError(f"Duplicate answer plan: {topic_id}")
        if topic_id not in expected:
            raise ValueError(f"Unknown answer-plan intent: {topic_id}")
        if (plan["service"], plan["parent_topic_id"]) != expected[topic_id]:
            raise ValueError(f"Wrong route for answer plan: {topic_id}")
        if plan["grounding_level"] not in GROUNDING_LEVELS:
            raise ValueError(f"Invalid grounding level for {topic_id}")
        if plan["answer_type"] not in ANSWER_TYPES:
            raise ValueError(f"Invalid answer type for {topic_id}")
        if not isinstance(plan["title"], str) or not plan["title"].strip():
            raise ValueError(f"Missing title for {topic_id}")
        if not _localized(plan["direct_answer"]):
            raise ValueError(f"Invalid direct answer for {topic_id}")
        for field in ("steps", "warnings"):
            if not isinstance(plan[field], list) or not all(_localized(item) for item in plan[field]):
                raise ValueError(f"Invalid {field} for {topic_id}")
        if not isinstance(plan["required_documents"], list) or not all(
            isinstance(item, str) and item.strip() for item in plan["required_documents"]
        ):
            raise ValueError(f"Invalid documents for {topic_id}")
        if not _localized(plan["clarification_question"], optional=True):
            raise ValueError(f"Invalid clarification question for {topic_id}")
        if plan["grounding_level"] == "SAFE_CLARIFICATION" and plan["clarification_question"] is None:
            raise ValueError(f"Safe clarification plan lacks a question: {topic_id}")
        if not _localized(plan["scope_note"]):
            raise ValueError(f"Invalid scope note for {topic_id}")
        if not isinstance(plan["official_source"], str) or not plan["official_source"].strip():
            raise ValueError(f"Invalid source name for {topic_id}")
        if not _official_url(plan["source_url"]):
            raise ValueError(f"Invalid official source URL for {topic_id}")
        reviewed = plan["last_verified"]
        if (
            not isinstance(reviewed, str)
            or len(reviewed) != 10
            or date.fromisoformat(reviewed).isoformat() != reviewed
            or date.fromisoformat(reviewed) > date.today()
        ):
            raise ValueError(f"Invalid source-review date for {topic_id}")
        plans[topic_id] = plan

    missing = sorted(set(expected) - set(plans))
    if missing or len(plans) != 264:
        raise ValueError(f"Answer-plan coverage must be 264/264; missing: {missing}")
    return plans


def plan_records() -> list[dict]:
    """Expose plans through the existing guidance-record interface."""
    return [
        {
            "service": plan["service"],
            "parent_topic_id": plan["parent_topic_id"],
            "query_topic_id": plan["query_topic_id"],
            "title": plan["title"],
            "guidance": plan["direct_answer"]["en"],
            "required_documents": plan["required_documents"],
            "official_source": plan["official_source"],
            "source_url": plan["source_url"],
            "last_verified": plan["last_verified"],
            "language": "mixed",
            "notes": f"Exact answer plan: {plan['grounding_level']}",
            "answer_plan": plan,
        }
        for plan in load_answer_plans().values()
    ]


def approved_plan_texts(record: dict, language: str) -> list[str]:
    plan = record.get("answer_plan") or load_answer_plans().get(record.get("query_topic_id"))
    if plan is None:
        return []
    texts = [plan["direct_answer"][language]]
    texts.extend(item[language] for item in plan["steps"])
    texts.extend(item[language] for item in plan["warnings"])
    if plan["clarification_question"]:
        texts.append(plan["clarification_question"][language])
    return texts


def render_plan_completion(record: dict, language: str) -> str:
    """Render a detailed SFT target without asking the model to reproduce links."""
    if language not in {"en", "bn"}:
        raise ValueError("Unsupported answer language")
    plan = record.get("answer_plan") or load_answer_plans().get(record.get("query_topic_id"))
    if plan is None:
        raise ValueError("Answer completion requires an exact answer plan")

    blocks = [plan["direct_answer"][language]]
    if plan["steps"]:
        heading = "ধাপগুলো:" if language == "bn" else "Steps:"
        items = "\n".join(
            f"{number}. {item[language]}"
            for number, item in enumerate(plan["steps"], start=1)
        )
        blocks.append(f"{heading}\n{items}")
    if plan["required_documents"]:
        heading = "প্রয়োজনীয় নথি ও তথ্য:" if language == "bn" else "Documents and information:"
        labels = (
            [_DOCUMENT_LABELS_BN.get(item, item) for item in plan["required_documents"]]
            if language == "bn" else plan["required_documents"]
        )
        items = "\n".join(f"- {item}" for item in labels)
        blocks.append(f"{heading}\n{items}")
    if plan["warnings"]:
        heading = "খেয়াল রাখুন:" if language == "bn" else "Important:"
        items = "\n".join(f"- {item[language]}" for item in plan["warnings"])
        blocks.append(f"{heading}\n{items}")
    if plan["clarification_question"]:
        blocks.append(plan["clarification_question"][language])
    return "\n\n".join(blocks)
