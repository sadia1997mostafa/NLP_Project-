"""Conservative high-precision service anchors.

These rules are frozen after DEV-only model selection.
They should not be changed after TEST evaluation begins.
"""

from __future__ import annotations

import re


SERVICE_ANCHOR_PATTERNS: dict[str, tuple[str, ...]] = {
    "NID": (
        r"\bnid\b",
        r"national id",
        r"national identity",
        r"\bvoter\b",
    ),
    "BIRTH_REGISTRATION": (
        r"\bbdris\b",
        r"birth registration",
        r"birth certificate",
        r"জন্ম নিবন্ধন",
    ),
    "PASSPORT": (
        r"\bpassport\b",
        r"e[- ]?passport",
    ),
    "TAX": (
        r"\be[- ]?tin\b",
        r"\btin\b",
        r"\btax\b",
        r"\btaxpayer\b",
    ),
    "POLICE_GD": (
        r"\bgd\b",
        r"general diary",
    ),
    "DRIVING_LICENCE": (
        r"\bbrta\b",
        r"driving licen[cs]e",
        r"learner licen[cs]e",
        r"\bdctc\b",
    ),
}


def service_anchors(text: str) -> list[str]:
    """Return all services with a matching conservative lexical anchor."""
    lowered = str(text).lower()
    return [
        service
        for service, patterns in SERVICE_ANCHOR_PATTERNS.items()
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns)
    ]


def unique_service_anchor(text: str) -> str | None:
    """Return the service only when exactly one service is anchored."""
    anchors = service_anchors(text)
    return anchors[0] if len(anchors) == 1 else None
