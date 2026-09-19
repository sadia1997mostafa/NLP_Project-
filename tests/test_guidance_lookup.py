"""Exact, fallback, OOD, and miss retrieval behavior."""

import unittest

from src.retrieval.lookup import GuidanceLookup


class GuidanceLookupTests(unittest.TestCase):
    def setUp(self):
        self.lookup = GuidanceLookup()

    def test_exact_topic_first(self):
        result = self.lookup.retrieve({
            "service": "PASSPORT", "parent_topic_id": "PASSPORT_APPLICATION",
            "query_topic_id": "PASSPORT_APPLICATION_ONLINE", "is_ood": False,
        })
        self.assertEqual(result["match_level"], "query_topic")
        self.assertEqual(result["record"]["title"], "Apply for an e-passport online")

    def test_parent_then_service_fallback(self):
        parent = self.lookup.retrieve({
            "service": "BIRTH_REGISTRATION", "parent_topic_id": "BR_REGISTRATION",
            "query_topic_id": "UNKNOWN", "is_ood": False,
        })
        service = self.lookup.retrieve({
            "service": "TAX", "parent_topic_id": "TAX_RETURN_FILING",
            "query_topic_id": "UNKNOWN", "is_ood": False,
        })
        self.assertEqual(parent["match_level"], "parent_topic")
        self.assertEqual(service["match_level"], "service")

    def test_ood_never_retrieves(self):
        result = self.lookup.retrieve({
            "service": "PASSPORT", "parent_topic_id": "PASSPORT_APPLICATION",
            "query_topic_id": "PASSPORT_APPLICATION_ONLINE", "is_ood": True,
        })
        self.assertEqual(result, {"status": "ood", "match_level": None, "record": None})

    def test_unknown_service_is_miss(self):
        result = self.lookup.retrieve({"service": "UNKNOWN", "is_ood": False})
        self.assertEqual(result["status"], "miss")


if __name__ == "__main__":
    unittest.main()
