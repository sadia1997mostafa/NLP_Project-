"""Deterministic lookup using Prothom's frozen routing IDs."""

from __future__ import annotations

from src.retrieval.corpus import load_records
from src.response.plans import plan_records


class GuidanceLookup:
    def __init__(self, records: list[dict] | None = None):
        if records is not None:
            self.records = records
        else:
            official_records = load_records()
            official_by_topic = {
                record["query_topic_id"]: record
                for record in official_records
                if record["query_topic_id"] is not None
            }
            exact_plans = []
            for record in plan_records():
                official = official_by_topic.get(record["query_topic_id"])
                if official is not None:
                    record = {**record, **official, "answer_plan": record["answer_plan"]}
                exact_plans.append(record)
            self.records = [
                record for record in official_records
                if record["query_topic_id"] is None
            ] + exact_plans
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
