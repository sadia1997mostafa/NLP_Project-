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
        self.assertEqual(response["source"]["url"], retrieval["record"]["source_url"])
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

    def test_unanchored_prediction_requests_clarification_at_every_match_level(self):
        understanding = {
            "service": "NID", "parent_topic_id": "NID_CORRECTION",
            "query_topic_id": "NID_CORRECTION_DOB", "is_ood": False,
            "service_routing": "xlm_roberta_fallback",
        }
        records = self.lookup.records
        for level, selected in (
            ("query_topic", records),
            ("parent_topic", [r for r in records if r["query_topic_id"] is None]),
            ("service", [r for r in records if r["parent_topic_id"] is None]),
        ):
            with self.subTest(level=level):
                retrieval = GuidanceLookup(selected).retrieve(understanding)
                self.assertEqual(retrieval["match_level"], level)
                response = construct_response(understanding, retrieval, [])
                self.assertEqual(response["state"], "clarification")
                self.assertIsNone(response["source"])
                self.assertEqual(response["required_documents"], [])

    def test_document_conditions_pass_through_without_invented_requirements(self):
        understanding = {
            "service": "DRIVING_LICENCE", "parent_topic_id": "DRIVING_LICENCE_LEARNER",
            "query_topic_id": "DRIVING_LICENCE_LEARNER_DOCUMENTS", "is_ood": False,
            "service_routing": "lexical_anchor",
        }
        retrieval = self.lookup.retrieve(understanding)
        response = construct_response(understanding, retrieval, [])
        self.assertEqual(response["state"], "answer")
        self.assertEqual(response["required_documents"], retrieval["record"]["required_documents"])
        self.assertIn("if different from NID", response["required_documents"][-1])

    def test_emergency_guidance_does_not_promise_dispatch(self):
        understanding = {
            "service": "POLICE_GD", "parent_topic_id": "POLICE_GD_GUIDANCE",
            "query_topic_id": "POLICE_GD_EMERGENCY_ROUTING", "is_ood": False,
            "service_routing": "lexical_anchor",
        }
        response = construct_response(understanding, self.lookup.retrieve(understanding), [])
        self.assertIn("999", response["body"])
        self.assertIn("cannot dispatch", response["body"])


if __name__ == "__main__":
    unittest.main()
