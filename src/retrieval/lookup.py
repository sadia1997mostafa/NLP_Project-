"""Deterministic lookup using Prothom's frozen routing IDs."""

from __future__ import annotations

from src.retrieval.corpus import load_records


class GuidanceLookup:
    def __init__(self, records: list[dict] | None = None):
        self.records = records if records is not None else load_records()
        self.by_key = {
            (record["service"], record["parent_topic_id"], record["query_topic_id"]): record
            for record in self.records
        }

    def retrieve(self, understanding: dict) -> dict:
        if understanding.get("is_ood"):
            return {"status": "ood", "match_level": None, "record": None}
        service = understanding.get("service")
        parent = understanding.get("parent_topic_id")
        topic = understanding.get("query_topic_id")
        for level, key in (
            ("query_topic", (service, parent, topic)),
            ("parent_topic", (service, parent, None)),
            ("service", (service, None, None)),
        ):
            if level == "query_topic" and (not parent or not topic):
                continue
            if level == "parent_topic" and not parent:
                continue
            record = self.by_key.get(key)
            if record is not None:
                return {"status": "found", "match_level": level, "record": record}
        return {"status": "miss", "match_level": None, "record": None}
