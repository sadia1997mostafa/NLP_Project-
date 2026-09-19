"""Conservative masking for common citizen identifiers and explicit personal fields."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PrivacyResult:
    privacy_present: bool
    privacy_types: list[str]
    safe_text: str
    warnings: list[str]


PATTERNS = (
    ("email", re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?!\w)", re.I)),
    ("phone", re.compile(r"(?<!\d)(?:\+?880[- ]?1[3-9]|01[3-9])(?:[- ]?\d){8}(?!\d)")),
    ("password", re.compile(r"\b(?:password|passcode|pin)\s*[:=]\s*([^\s,;.!?]{4,64})", re.I)),
    ("otp", re.compile(r"(?:\b(?:otp|verification code|one.time code)\b|ওটিপি)\s*(?:is|[:=])?\s*(\d{4,8})(?!\d)", re.I)),
    ("birth_registration", re.compile(
        r"(?:\b(?:birth\s+(?:registration|certificate)|jonmo\s+(?:nibondhon|sonod))\b|জন্ম\s+(?:নিবন্ধন|সনদ))"
        r"\s*(?:number|no\.?|id|নম্বর)?\s*[:=#-]?\s*((?:\d[ -]?){3,19}\d)(?!\d)", re.I,
    )),
    ("passport", re.compile(
        r"(?:\bpassport\b|পাসপোর্ট)\s*(?:number|no\.?|id|নম্বর)?\s*[:=#-]?\s*"
        r"((?=[A-Z0-9/-]{4,24}(?![A-Z0-9/-]))(?=[A-Z0-9/-]*\d)[A-Z0-9/-]{4,24})", re.I,
    )),
    ("tin", re.compile(
        r"(?:\b(?:e-?tin|tax\s+identification\s+number)\b|(?:ই-?)টিন)"
        r"\s*(?:number|no\.?|id|নম্বর)?\s*[:=#-]?\s*((?:\d[ -]?){8,19}\d)(?!\d)", re.I,
    )),
    ("driving_licence", re.compile(
        r"(?:\b(?:driving\s+licen[cs]e|dl)\b|ড্রাইভিং\s+লাইসেন্স)"
        r"\s*(?:number|no\.?|id|নম্বর)?\s*[:=#-]?\s*"
        r"((?=[A-Z0-9/-]{4,24}(?![A-Z0-9/-]))(?=[A-Z0-9/-]*\d)[A-Z0-9/-]{4,24})", re.I,
    )),
    ("application_id", re.compile(
        r"(?:\b(?:application|registration|tracking)\s+(?:id|number|no\.?)\b|"
        r"\breference\s+(?:code|number|no\.?)\b|(?:আবেদন|রেজিস্ট্রেশন)\s+(?:আইডি|নম্বর))"
        r"\s*[:=#-]?\s*((?=[A-Z0-9/-]{4,30}(?![A-Z0-9/-]))(?=[A-Z0-9/-]*\d)[A-Z0-9/-]{4,30})", re.I,
    )),
    ("nid", re.compile(r"\b(?:nid|national id|voter id)\s*(?:number|no\.?|is|[:=#])?\s*[:=#]?\s*((?:\d[ -]?){9,16}\d)(?!\d)", re.I)),
    ("nid", re.compile(r"(?<!\d)(?:\d{17}|\d{13}|\d{10})(?!\d)")),
    ("name", re.compile(r"\bamar nam\s*(?:is|:)\s*([^,.;\n!?]{2,60})", re.I)),
    ("address", re.compile(r"\bamar thikana\s*(?:is|:)\s*([^;\n!?]{4,120})", re.I)),
    ("passport", re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,2}\d{7,8}(?![A-Za-z0-9])", re.I)),
    ("date_of_birth", re.compile(r"\b(?:DOB|date of birth|জন্ম তারিখ)\s*[:：-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})", re.I)),
    ("name", re.compile(r"(?:my name is|name\s*[:：]|আমার নাম|নাম\s*[:：])\s*([^,.;\n!?।]{2,60})", re.I)),
    ("address", re.compile(r"(?:my address is|address\s*[:：]|আমার ঠিকানা|ঠিকানা\s*[:：])\s*([^;\n!?।]{4,120})", re.I)),
)


def detect_privacy(text: str) -> PrivacyResult:
    detected: list[tuple[int, int, str]] = []
    normalized_digits = text.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    for kind, pattern in PATTERNS:
        searchable = normalized_digits if kind in {
            "phone", "nid", "otp", "birth_registration", "passport", "tin",
            "driving_licence", "application_id", "date_of_birth",
        } else text
        for match in pattern.finditer(searchable):
            value = match.group(1) if match.lastindex else match.group(0)
            start, end = match.span(1) if match.lastindex else match.span()
            if value.strip():
                detected.append((start, end, kind))
    spans: list[tuple[int, int, str]] = []
    for start, end, kind in sorted(detected, key=lambda span: (-(span[1] - span[0]), span[0])):
        if not any(start < old_end and end > old_start for old_start, old_end, _ in spans):
            spans.append((start, end, kind))
    spans.sort(key=lambda span: span[0])
    fragments, cursor = [], 0
    for start, end, kind in spans:
        fragments.extend((text[cursor:start], f"[{kind.upper()}]"))
        cursor = end
    fragments.append(text[cursor:])
    kinds = list(dict.fromkeys(kind for _, _, kind in spans))
    return PrivacyResult(
        privacy_present=bool(spans),
        privacy_types=kinds,
        safe_text="".join(fragments),
        warnings=(["Personal information was detected. Avoid sharing identifiers unless required by an official service."] if spans else []),
    )
