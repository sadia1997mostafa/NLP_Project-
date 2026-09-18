"""Load and validate source-backed guidance against frozen taxonomy IDs."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from src.models.hierarchy import load_contract


DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / "knowledge_base/guidance.json"
REQUIRED_FIELDS = {
    "service", "parent_topic_id", "query_topic_id", "title", "guidance",
    "required_documents", "official_source", "source_url", "last_verified", "language", "notes",
}


def load_records(path: Path = DEFAULT_CORPUS) -> list[dict]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Guidance corpus must be a list")
    services = load_contract()["services"]
    seen = set()
    for number, record in enumerate(records, start=1):
        if not isinstance(record, dict) or set(record) != REQUIRED_FIELDS:
            raise ValueError(f"Corpus record {number} has invalid fields")
        service, parent, topic = (record[key] for key in ("service", "parent_topic_id", "query_topic_id"))
        if not isinstance(service, str) or any(
            value is not None and not isinstance(value, str) for value in (parent, topic)
        ):
            raise ValueError(f"Corpus record {number} has invalid route types")
        if service not in services:
            raise ValueError(f"Corpus record {number} has unknown service")
        parents = services[service]["parent_topics"]
        if parent is not None and parent not in parents:
            raise ValueError(f"Corpus record {number} has unknown parent topic")
        if topic is not None and (parent is None or topic not in parents[parent]["query_topics"]):
            raise ValueError(f"Corpus record {number} has unknown query topic")
        key = (service, parent, topic)
        if key in seen:
            raise ValueError(f"Duplicate guidance route: {key}")
        seen.add(key)
        if not isinstance(record["source_url"], str):
            raise ValueError(f"Corpus record {number} has invalid source URL")
        url = urlparse(record["source_url"])
        if (url.scheme != "https" or not url.hostname or not url.hostname.endswith(".gov.bd")
                or url.username is not None or url.password is not None):
            raise ValueError(f"Corpus record {number} lacks an official HTTPS source")
        reviewed = record["last_verified"]
        if (not isinstance(reviewed, str) or len(reviewed) != 10
                or date.fromisoformat(reviewed).isoformat() != reviewed
                or date.fromisoformat(reviewed) > date.today()):
            raise ValueError(f"Corpus record {number} has invalid review date")
        if record["language"] not in {"en", "bn", "mixed"}:
            raise ValueError(f"Corpus record {number} has invalid language")
        if not all(isinstance(record[key], str) and record[key].strip() for key in ("title", "guidance", "official_source")):
            raise ValueError(f"Corpus record {number} has empty content")
        if not isinstance(record["required_documents"], list) or not all(
            isinstance(item, str) and item.strip() for item in record["required_documents"]
        ):
            raise ValueError(f"Corpus record {number} has invalid documents")
        if not isinstance(record["notes"], str):
            raise ValueError(f"Corpus record {number} has invalid notes")
    return records
