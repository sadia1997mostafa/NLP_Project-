"""Conservative, deterministic normalization for Bangla/code-mixed queries."""

from __future__ import annotations

import re
import unicodedata


_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Apply Unicode NFC and collapse accidental whitespace only."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def normalized_key(text: str) -> str:
    """Return a case-insensitive key for duplicate/leakage checks."""
    return normalize_text(text).casefold()
