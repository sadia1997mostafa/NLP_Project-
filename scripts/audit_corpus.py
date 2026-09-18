"""Validate curated guidance and report exact coverage without loading models."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from src.models.hierarchy import load_contract
from src.retrieval.corpus import DEFAULT_CORPUS, load_records


def coverage_report(records: list[dict], *, today: date | None = None) -> dict:
    today = today or date.today()
    services = {}
    for service, definition in load_contract()["services"].items():
        selected = [record for record in records if record["service"] == service]
        topics = {
            topic for parent in definition["parent_topics"].values()
            for topic in parent["query_topics"]
        }
        covered = {record["query_topic_id"] for record in selected if record["query_topic_id"]}
        services[service] = {
            "records": len(selected),
            "service_records": sum(record["parent_topic_id"] is None for record in selected),
            "parent_records": sum(
                record["parent_topic_id"] is not None and record["query_topic_id"] is None
                for record in selected
            ),
            "exact_topics": len(covered),
            "total_topics": len(topics),
            "uncovered_topics": sorted(topics - covered),
        }
    return {
        "records": len(records),
        "exact_topics": sum(item["exact_topics"] for item in services.values()),
        "total_topics": sum(item["total_topics"] for item in services.values()),
        "official_sources": len({record["source_url"] for record in records}),
        "records_with_documents": sum(bool(record["required_documents"]) for record in records),
        "review_due": [
            record["query_topic_id"] or record["parent_topic_id"] or record["service"]
            for record in records
            if (today - date.fromisoformat(record["last_verified"])).days > 90
        ],
        "services": services,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--json", action="store_true", help="Include every uncovered topic ID")
    args = parser.parse_args()
    report = coverage_report(load_records(args.corpus))
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"Records: {report['records']}; exact topics: {report['exact_topics']}/{report['total_topics']}")
    print(f"Official sources: {report['official_sources']}; document lists: {report['records_with_documents']}")
    for service, item in report["services"].items():
        print(f"{service}: {item['exact_topics']}/{item['total_topics']} exact; "
              f"{item['parent_records']} parent; {item['service_records']} service")
    print(f"Review older than 90 days: {len(report['review_due'])}")
    print("Exact coverage is curated-content coverage, not classifier accuracy or completeness.")


if __name__ == "__main__":
    main()
