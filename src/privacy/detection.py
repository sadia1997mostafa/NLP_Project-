"""Context-aware masking for citizen identifiers and explicit personal fields."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PrivacyResult:
    privacy_present: bool
    privacy_types: list[str]
    safe_text: str
    warnings: list[str]


FLAGS = re.IGNORECASE
DIGIT_VALUE = r"(?:\d[ -]?){3,19}\d"
TOKEN_VALUE = (
    r"(?=[A-Z0-9/-]{4,30}(?![A-Z0-9/-]))"
    r"(?=[A-Z0-9/-]*\d)[A-Z0-9/-]{4,30}"
)
LABEL = r"(?:number|no\.?|num|id|code|serial|nombor|নম্বর|নং|আইডি|কোড)"
SEPARATOR = r"\s*(?:(?:is|holo|hocche|হলো|হচ্ছে)\s+|[:=#-]\s*)?"


def _compiled(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, FLAGS)


# More specific labelled patterns must precede generic and standalone patterns.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", _compiled(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?!\w)")),
    ("phone", _compiled(
        r"(?<!\d)(?:\+?880[- ]?1[3-9]|01[3-9])(?:[- ]?\d){8}(?!\d)"
    )),
    ("password", _compiled(
        r"(?:\b(?:password|passcode|pin)\b|পাসওয়ার্ড|পাসকোড|পিন)"
        r"\s*(?:(?:is|holo|hocche|হলো|হচ্ছে)\s+|[:=]\s*)([^\s,;.!?।]{4,64})"
    )),
    ("otp", _compiled(
        r"(?:\b(?:otp|verification\s+code|one[ -]?time\s+(?:password|code)|security\s+code)\b|"
        r"ওটিপি|ভেরিফিকেশন\s+কোড)\s*(?:code\s*)?(?:ta|টি)?"
        r"\s*(?:(?:is|holo|hocche|হলো|হচ্ছে)\s+|[:=]\s*)?(\d{4,8})(?!\d)"
    )),
    ("birth_registration", _compiled(
        rf"(?:\b(?:birth\s+(?:registration|certificate)|jonmo\s+"
        rf"(?:nibondhon|nibondon|nibandhan|sonod|certificate))\b|"
        rf"জন্ম\s+(?:নিবন্ধন|সনদ))\s*(?:{LABEL})?{SEPARATOR}({DIGIT_VALUE})(?!\d)"
    )),
    ("passport", _compiled(
        rf"(?:\b(?:e[ -]?)?passport\b|পাসপোর্ট)\s*(?:{LABEL})?{SEPARATOR}({TOKEN_VALUE})"
    )),
    ("tin", _compiled(
        rf"(?:\b(?:e[ -]?tin|tin|tax\s+(?:identification|id))\b|(?:ই[ -]?)?টিন|"
        rf"করদাতা\s+শনাক্তকরণ)\s*(?:{LABEL})?{SEPARATOR}({DIGIT_VALUE})(?!\d)"
    )),
    ("driving_licence", _compiled(
        rf"(?:\b(?:(?:driving|learner)\s+licen[cs]e|brta\s+licen[cs]e|dl)\b|"
        rf"(?:ড্রাইভিং|লার্নার)\s+লাইসেন্স)\s*(?:{LABEL})?{SEPARATOR}({TOKEN_VALUE})"
    )),
    ("application_id", _compiled(
        rf"(?:\b(?:application|registration|tracking|reference)\s+{LABEL}\b|"
        rf"(?:আবেদন|রেজিস্ট্রেশন|ট্র্যাকিং|রেফারেন্স)\s+(?:নম্বর|নং|আইডি|কোড))"
        rf"{SEPARATOR}({TOKEN_VALUE})"
    )),
    ("nid", _compiled(
        rf"(?:\b(?:nid|national\s+id|voter\s+(?:id|card))\b|"
        rf"জাতীয়\s+পরিচয়পত্র|ভোটার\s+(?:আইডি|কার্ড))"
        rf"\s*(?:{LABEL})?{SEPARATOR}({DIGIT_VALUE})(?!\d)"
    )),
    ("bank_account", _compiled(
        rf"(?:\b(?:bank\s+account|account)\s+(?:number|no\.?|id)\b|"
        rf"ব্যাংক\s+হিসাব\s+(?:নম্বর|নং))\s*{SEPARATOR}({TOKEN_VALUE})"
    )),
    ("payment_card", _compiled(
        rf"(?:\b(?:(?:credit|debit)\s+card|card)\s+(?:number|no\.?)\b|"
        rf"(?:ক্রেডিট|ডেবিট)?\s*কার্ড\s+(?:নম্বর|নং))\s*{SEPARATOR}({DIGIT_VALUE})(?!\d)"
    )),
    ("date_of_birth", _compiled(
        r"(?:\b(?:dob|date\s+of\s+birth|birth\s+date)\b|জন্ম\s+তারিখ)\s*[:：=-]?\s*"
        r"((?:\d{1,2}[-/.]\d{1,2}[-/.]\d{4})|(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}))"
    )),
    ("name", _compiled(
        r"\b(?:my|amar|amr)\s+(?:full\s+)?(?:name|nam|naam)\s*"
        r"(?:(?:is|holo|hocche)\s+|[:=]\s*)([^,.;\n!?।]{2,60})"
    )),
    ("name", _compiled(
        r"(?:(?:আমার|পিতার|মাতার)\s+নাম|নাম\s*[:：])\s*"
        r"(?:(?:হলো|হচ্ছে)\s+|[:=]\s*)?([^,.;\n!?।]{2,60})"
    )),
    ("name", _compiled(
        r"\b(?:father(?:'s)?|mother(?:'s)?|babar|mayer)\s+(?:name|nam)\s*"
        r"(?:(?:is|holo|hocche)\s+|[:=]\s*)([^,.;\n!?।]{2,60})"
    )),
    ("address", _compiled(
        r"(?:\b(?:my|amar|amr)\s+(?:present\s+|permanent\s+)?(?:address|thikana)|"
        r"\baddress)\s*"
        r"(?:(?:is|holo|hocche)\s+|[:=]\s*)([^;\n!?।]{4,120})"
    )),
    ("address", _compiled(
        r"(?:(?:আমার\s+)?(?:বর্তমান\s+|স্থায়ী\s+)?ঠিকানা)\s*"
        r"(?:(?:হলো|হচ্ছে)\s+|[:=]\s*)([^;\n!?।]{4,120})"
    )),
    ("identifier", _compiled(
        rf"(?:\b(?:identifier|personal\s+id|customer\s+id|user\s+id|serial|id|number|no\.?|code)\b|"
        rf"(?:ব্যক্তিগত\s+)?(?:আইডি|নম্বর|নং|কোড|সিরিয়াল))\s*{SEPARATOR}({TOKEN_VALUE})"
    )),
    ("passport", _compiled(r"(?<![A-Za-z0-9])[A-Z]{1,2}\d{7,8}(?![A-Za-z0-9])")),
    ("identifier", _compiled(r"(?<!\d)(?:\d{17}|\d{13}|\d{10})(?!\d)")),
)


DIGIT_NORMALIZED_TYPES = {
    "phone", "nid", "otp", "birth_registration", "passport", "tin",
    "driving_licence", "application_id", "date_of_birth", "bank_account",
    "payment_card", "identifier",
}


def detect_privacy(text: str) -> PrivacyResult:
    detected: list[tuple[int, int, str, int]] = []
    normalized_digits = text.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    for priority, (kind, pattern) in enumerate(PATTERNS):
        searchable = normalized_digits if kind in DIGIT_NORMALIZED_TYPES else text
        for match in pattern.finditer(searchable):
            value = match.group(1) if match.lastindex else match.group(0)
            start, end = match.span(1) if match.lastindex else match.span()
            if value.strip():
                detected.append((start, end, kind, priority))

    # Prefer the largest value span, then the earlier and more specific rule.
    spans: list[tuple[int, int, str, int]] = []
    for candidate in sorted(
        detected,
        key=lambda span: (-(span[1] - span[0]), span[0], span[3]),
    ):
        start, end, _, _ = candidate
        if not any(start < old_end and end > old_start for old_start, old_end, _, _ in spans):
            spans.append(candidate)
    spans.sort(key=lambda span: span[0])

    fragments, cursor = [], 0
    for start, end, kind, _ in spans:
        fragments.extend((text[cursor:start], f"[{kind.upper()}]"))
        cursor = end
    fragments.append(text[cursor:])
    kinds = list(dict.fromkeys(kind for _, _, kind, _ in spans))
    return PrivacyResult(
        privacy_present=bool(spans),
        privacy_types=kinds,
        safe_text="".join(fragments),
        warnings=(
            ["Personal information was detected. Avoid sharing identifiers unless required by an official service."]
            if spans else []
        ),
    )
