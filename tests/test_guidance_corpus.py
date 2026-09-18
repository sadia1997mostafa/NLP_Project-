"""Check every curated record against the frozen routing contract."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.retrieval.corpus import load_records
from src.retrieval.lookup import GuidanceLookup
from scripts.audit_corpus import coverage_report


class GuidanceCorpusTests(unittest.TestCase):
    def test_all_services_have_general_guidance(self):
        records = load_records()
        general = {item["service"] for item in records if item["parent_topic_id"] is None}
        self.assertEqual(general, {"NID", "BIRTH_REGISTRATION", "PASSPORT", "TAX", "POLICE_GD", "DRIVING_LICENCE"})
        report = coverage_report(records)
        self.assertEqual(report["total_topics"], 264)
        self.assertGreaterEqual(report["exact_topics"], 50)
        for service, coverage in report["services"].items():
            with self.subTest(service=service):
                self.assertGreaterEqual(coverage["exact_topics"], 7)
                self.assertEqual(coverage["service_records"], 1)
                self.assertEqual(
                    coverage["exact_topics"] + len(coverage["uncovered_topics"]),
                    coverage["total_topics"],
                )

    def test_every_exact_record_resolves_without_fallback(self):
        records = load_records()
        lookup = GuidanceLookup(records)
        for record in records:
            if record["query_topic_id"]:
                with self.subTest(topic=record["query_topic_id"]):
                    result = lookup.retrieve({**record, "is_ood": False})
                    self.assertEqual(result["match_level"], "query_topic")
                    self.assertEqual(result["record"], record)

    def test_audit_reports_stale_reviews_and_does_not_count_fallback_as_exact(self):
        records = load_records()
        report = coverage_report(records, today=date(2027, 1, 1))
        self.assertEqual(len(report["review_due"]), len(records))
        self.assertIn("TAX_RETURN_DEADLINE", report["services"]["TAX"]["uncovered_topics"])
        self.assertEqual(report["exact_topics"], sum(bool(r["query_topic_id"]) for r in records))

    def test_rejects_unknown_topic_and_unofficial_source(self):
        records = load_records()
        for field, value in (
            ("query_topic_id", "UNKNOWN"), ("parent_topic_id", "NID_CORRECTION"),
            ("service", []), ("source_url", None),
            ("source_url", "https://example.com/"),
            ("source_url", "https://bdris.gov.bd.example.com/"),
            ("source_url", "https://user@bdris.gov.bd/"),
            ("last_verified", "2099-01-01"), ("last_verified", "20260918"),
            ("required_documents", [""]), ("notes", []),
        ):
            changed = json.loads(json.dumps(records))
            changed[-1][field] = value
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "guidance.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_records(path)

    def test_duplicate_routes_are_rejected(self):
        records = load_records()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "guidance.json"
            path.write_text(json.dumps(records + [records[-1]]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_records(path)


if __name__ == "__main__":
    unittest.main()
