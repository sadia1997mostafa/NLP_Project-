"""End-to-end API behavior with a frozen-contract-shaped predictor."""

import unittest

from fastapi.testclient import TestClient

from app.server import create_app
from src.models.hierarchy import load_contract
from src.pipeline.service import QueryPipeline
from src.retrieval.lookup import GuidanceLookup


class PartnerBIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.services = load_contract()["services"]
        self.queries = {
            "NID": "NID help", "BIRTH_REGISTRATION": "birth registration help",
            "PASSPORT": "passport help", "TAX": "tax help",
            "POLICE_GD": "online GD help", "DRIVING_LICENCE": "driving licence help",
        }

        def predict(text):
            self.calls.append(text)
            service = next((key for key, term in self.queries.items() if term.lower() in text.lower()), text.split()[0])
            if service not in self.services:
                return {"text": text, "service": service, "is_ood": service == "OOD", "priority": "Low"}
            parent_id, parent = next(iter(self.services[service]["parent_topics"].items()))
            topic_id = next(iter(parent["query_topics"]))
            return {
                "text": text, "service": service, "parent_topic_id": parent_id,
                "query_topic_id": topic_id, "query_topic": parent["query_topics"][topic_id]["display_name"],
                "priority": "Low", "is_ood": False,
            }

        self.client = TestClient(create_app(QueryPipeline(predict, GuidanceLookup())))

    def test_all_six_services_reach_their_own_corpus_namespace(self):
        for service in self.services:
            with self.subTest(service=service):
                response = self.client.post("/api/analyze", json={"text": self.queries[service]})
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["response"]["state"], "answer")
                self.assertEqual(body["response"]["match_level"], "service")
                self.assertIsNotNone(body["response"]["source"])
                self.assertIsNone(body["retrieval"]["record"])
                chosen = self.client.post("/api/guidance", json={
                    "service": service, "parent_topic_id": None, "query_topic_id": None,
                })
                self.assertEqual(chosen.status_code, 200)
                self.assertEqual(chosen.json()["response"]["state"], "answer")
                self.assertEqual(chosen.json()["retrieval"]["record"]["service"], service)

    def test_ood_and_missing_record_do_not_claim_a_source(self):
        for query, expected in (("OOD help", "clarification"), ("UNKNOWN help", "clarification")):
            body = self.client.post("/api/analyze", json={"text": query}).json()
            self.assertEqual(body["response"]["state"], expected)
            self.assertIsNone(body["response"]["source"])

    def test_sensitive_text_is_ephemeral_in_api_result(self):
        raw = "PASSPORT my email is citizen@example.com"
        response = self.client.post("/api/analyze", json={"text": raw})
        self.assertEqual(self.calls[-1], raw)
        self.assertTrue(response.json()["privacy_present"])
        self.assertNotIn("citizen@example.com", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_repeated_requests_use_same_predictor_instance(self):
        for _ in range(2):
            self.assertEqual(self.client.post("/api/analyze", json={"text": "TAX help"}).status_code, 200)
        self.assertEqual(self.calls, ["TAX help", "TAX help"])

    def test_status_records_frozen_runtime(self):
        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["runtime_freeze_commit"], "38a343d")
        self.assertEqual(status.json()["results_commit"], "f2f4e3e")


if __name__ == "__main__":
    unittest.main()
