"""Response states must not invent details outside the corpus."""

import unittest

from src.response.controller import construct_response
from src.retrieval.lookup import GuidanceLookup


class ResponseControllerTests(unittest.TestCase):
    def setUp(self):
        self.lookup = GuidanceLookup()

    def test_exact_response_cites_its_record(self):
        understanding = {
            "service": "TAX", "parent_topic_id": "TAX_RETURN_FILING",
            "query_topic_id": "TAX_RETURN_ONLINE_SUBMISSION", "priority": "Low", "is_ood": False,
        }
        retrieval = self.lookup.retrieve(understanding)
        response = construct_response(understanding, retrieval, ["Sensitive details detected"])
        self.assertEqual(response["state"], "answer")
        self.assertIsNone(response["scope_note"])
        self.assertEqual(response["source"]["url"], "https://etaxnbr.gov.bd/")
        self.assertEqual(response["privacy_warnings"], ["Sensitive details detected"])

    def test_fallback_is_labeled_general(self):
        understanding = {
            "service": "TAX", "parent_topic_id": "TAX_RETURN_FILING",
            "query_topic_id": "TAX_RETURN_DEADLINE", "is_ood": False,
        }
        response = construct_response(understanding, self.lookup.retrieve(understanding), [])
        self.assertEqual(response["state"], "answer")
        self.assertIn("general guidance", response["scope_note"])
        self.assertNotIn("deadline", response["body"].lower())

    def test_ood_and_miss_have_no_source_or_fabricated_guidance(self):
        for understanding in (
            {"service": "TAX", "is_ood": True},
            {"service": "UNKNOWN", "is_ood": False},
        ):
            response = construct_response(understanding, self.lookup.retrieve(understanding), [])
            self.assertIn(response["state"], {"clarification", "unavailable"})
            self.assertIsNone(response["source"])
            self.assertEqual(response["required_documents"], [])

    def test_unanchored_service_only_match_requests_clarification(self):
        understanding = {
            "service": "NID", "parent_topic_id": "NID_CORRECTION",
            "query_topic_id": "NID_CORRECTION_DOB", "is_ood": False,
            "service_routing": "xlm_roberta_fallback",
        }
        retrieval = self.lookup.retrieve(understanding)
        self.assertEqual(retrieval["match_level"], "service")
        response = construct_response(understanding, retrieval, [])
        self.assertEqual(response["state"], "clarification")
        self.assertIsNone(response["source"])


if __name__ == "__main__":
    unittest.main()
