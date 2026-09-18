"""Validated, source-linked fact plans for controlled answer realization."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.retrieval.corpus import load_records


FACTBOOK = Path(__file__).resolve().parents[2] / "knowledge_base/answer_facts.json"
VERBS = {
    "use": ("use", "ব্যবহার করুন"),
    "open": ("open", "খুলুন"),
    "choose": ("choose", "বেছে নিন"),
    "enter": ("enter", "লিখুন"),
    "submit": ("submit", "জমা দিন"),
    "check": ("check", "যাচাই করুন"),
    "prepare": ("prepare", "প্রস্তুত রাখুন"),
    "bring": ("bring", "সঙ্গে নিন"),
    "upload": ("upload", "আপলোড করুন"),
    "keep": ("keep", "সংরক্ষণ করুন"),
    "print": ("print", "প্রিন্ট করুন"),
    "download": ("download", "ডাউনলোড করুন"),
    "sign_in": ("sign in to", "সাইন ইন করুন"),
    "register": ("register on", "নিবন্ধন করুন"),
    "follow": ("follow", "অনুসরণ করুন"),
    "contact": ("contact", "যোগাযোগ করুন"),
    "attend": ("attend", "উপস্থিত হন"),
    "report": ("report", "রিপোর্ট করুন"),
    "pay": ("pay", "পরিশোধ করুন"),
    "call": ("call", "কল করুন"),
    "review": ("review", "মিলিয়ে দেখুন"),
    "complete": ("complete", "পূরণ করুন"),
    "provide": ("provide", "দিন"),
    "find": ("find", "খুঁজে বের করুন"),
    "correct": ("correct", "সংশোধন করুন"),
    "arrange": ("arrange", "সম্পন্ন করুন"),
}


def route_key(record: dict) -> str:
    return record["query_topic_id"] or record["parent_topic_id"] or record["service"]


def _localized(value: object) -> bool:
    return isinstance(value, dict) and set(value) == {"en", "bn"} and all(
        isinstance(value[language], str) and value[language].strip()
        for language in ("en", "bn")
    )


@lru_cache(maxsize=1)
def load_factbook(path: Path = FACTBOOK) -> dict[str, list[dict]]:
    factbook = json.loads(path.read_text(encoding="utf-8"))
    expected = {route_key(record) for record in load_records()}
    if not isinstance(factbook, dict) or set(factbook) != expected:
        raise ValueError("Answer factbook must cover every curated route exactly")
    for route, units in factbook.items():
        if not isinstance(units, list) or not units:
            raise ValueError(f"No answer facts for {route}")
        if not isinstance(units[0], dict) or units[0].get("kind") != "action":
            raise ValueError(f"First fact must be an action for {route}")
        for unit in units:
            if not isinstance(unit, dict):
                raise ValueError(f"Invalid answer fact for {route}")
            if unit.get("kind") == "action":
                if (set(unit) - {"kind", "verb", "target", "place", "when"}
                        or unit.get("verb") not in VERBS
                        or not _localized(unit.get("target"))
                        or any(not _localized(unit[key]) for key in ("place", "when") if key in unit)):
                    raise ValueError(f"Invalid action fact for {route}")
            elif unit.get("kind") == "notice":
                if (set(unit) not in ({"kind", "text"}, {"kind", "text", "prominence"})
                        or not _localized(unit.get("text"))
                        or ("prominence" in unit and unit["prominence"] != "lead")):
                    raise ValueError(f"Invalid notice fact for {route}")
            else:
                raise ValueError(f"Unknown answer fact type for {route}")
    return factbook


def render_fact(unit: dict, language: str) -> str:
    if unit["kind"] == "notice":
        return unit["text"][language]
    verb_en, verb_bn = VERBS[unit["verb"]]
    target = unit["target"][language]
    place = unit.get("place", {}).get(language)
    when = unit.get("when", {}).get(language)
    if language == "bn":
        core = " ".join(part for part in (place, target, verb_bn) if part)
        return f"{when}, {core}।" if when else f"{core}।"
    core = f"{verb_en} {target}{' ' + place if place else ''}"
    sentence = f"if {when}, {core}" if when else core
    return f"{sentence[0].upper()}{sentence[1:]}."


def facts_for(record: dict) -> list[dict]:
    return load_factbook()[route_key(record)]
