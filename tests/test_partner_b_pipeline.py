"""Privacy and backend contract tests that do not require model artifacts."""

import asyncio
import time
import unittest
from threading import Event

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.server import create_app
from src.pipeline.service import QueryPipeline
from src.privacy.detection import detect_privacy
from src.retrieval.corpus import load_records


def fake_predictor(text: str) -> dict:
    return {"text": text, "service": "NID", "query_topic_id": "NID_TEST", "is_ood": False}


class PrivacyTests(unittest.TestCase):
    def test_masks_identifiers_and_preserves_query(self):
        result = detect_privacy("My NID 1234567890 and phone 01712345678 need an update")
        self.assertEqual(result.privacy_types, ["nid", "phone"])
        self.assertEqual(result.safe_text, "My NID [NID] and phone [PHONE] need an update")
        self.assertTrue(result.privacy_present)

    def test_masks_explicit_name_and_address(self):
        result = detect_privacy("my name is Ayesha Rahman, address: 12 Lake Road; help")
        self.assertIn("[NAME]", result.safe_text)
        self.assertIn("[ADDRESS]", result.safe_text)
        self.assertNotIn("Ayesha", result.safe_text)
        self.assertNotIn("Lake Road", result.safe_text)

    def test_masks_credentials_and_formatted_id_without_masking_service_words(self):
        result = detect_privacy("NID number: 123-456-7890, OTP is 123456, password: secret123; correct my NID")
        self.assertEqual(result.safe_text, "NID number: [NID], OTP is [OTP], password: [PASSWORD]; correct my NID")
        self.assertEqual(result.privacy_types, ["nid", "otp", "password"])

    def test_masks_banglish_personal_fields(self):
        result = detect_privacy("amar nam: Ayesha Rahman, amar thikana: 12 Lake Road; NID correction")
        self.assertNotIn("Ayesha Rahman", result.safe_text)
        self.assertNotIn("12 Lake Road", result.safe_text)
        self.assertIn("NID correction", result.safe_text)

    def test_query_without_personal_data(self):
        result = detect_privacy("How do I apply for a passport?")
        self.assertFalse(result.privacy_present)
        self.assertEqual(result.safe_text, "How do I apply for a passport?")

    def test_masks_country_code_and_bangla_numerals(self):
        result = detect_privacy("Call +8801712345678 or ০১৭১২৩৪৫৬৭৮")
        self.assertEqual(result.safe_text, "Call [PHONE] or [PHONE]")
        self.assertEqual(result.privacy_types, ["phone"])


class PipelineTests(unittest.TestCase):
    def test_classifier_receives_original_but_response_is_masked(self):
        seen = []

        def predict(text):
            seen.append(text)
            return fake_predictor(text)

        result = QueryPipeline(predict).analyze("NID 1234567890 update")
        self.assertEqual(seen, ["NID 1234567890 update"])
        self.assertEqual(result["understanding"]["text"], "NID [NID] update")
        self.assertNotIn("1234567890", str(result))

    def test_http_contract_and_validation(self):
        client = TestClient(create_app(QueryPipeline(fake_predictor)))
        response = client.post("/api/analyze", json={"text": "NID 1234567890 update"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["privacy_types"], ["nid"])
        self.assertNotIn("1234567890", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(client.post("/api/analyze", json={"text": " "}).status_code, 400)

    def test_serves_interface_and_assets(self):
        client = TestClient(create_app(QueryPipeline(fake_predictor)))
        self.assertIn("NagorikSheba", client.get("/").text)
        self.assertEqual(client.get("/static/styles.css").status_code, 200)
        self.assertEqual(client.get("/static/main.js").status_code, 200)

    def test_http_returns_sourced_document_checklist(self):
        def predict(text):
            return {
                "text": text, "service": "PASSPORT", "parent_topic_id": "PASSPORT_DOCUMENTS",
                "query_topic_id": "PASSPORT_DOCUMENTS_REQUIRED", "is_ood": False,
                "service_routing": "lexical_anchor",
            }

        client = TestClient(create_app(QueryPipeline(predict)))
        response = client.post("/api/analyze", json={"text": "Passport documents?"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["response"]["state"], "answer")
        self.assertEqual(payload["understanding"]["resolved_topic_id"], "PASSPORT_DOCUMENTS_REQUIRED")
        self.assertIsNone(payload["retrieval"]["record"])
        response = client.post("/api/guidance", json={
            "service": "PASSPORT", "parent_topic_id": "PASSPORT_DOCUMENTS",
            "query_topic_id": "PASSPORT_DOCUMENTS_REQUIRED",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        record = payload["retrieval"]["record"]
        answer = payload["response"]
        self.assertEqual(answer["state"], "answer")
        self.assertEqual(answer["required_documents"], record["required_documents"])
        self.assertGreater(len(answer["required_documents"]), 0)
        self.assertEqual(answer["source"]["url"], record["source_url"])
        self.assertIn('id="document-list"', client.get("/").text)

    def test_unsupported_or_conflicting_service_does_not_get_an_answer(self):
        client = TestClient(create_app(QueryPipeline(fake_predictor)))
        for query in ("What is the weather on Mars?", "NID and passport help"):
            with self.subTest(query=query):
                result = client.post("/api/analyze", json={"text": query}).json()
                self.assertEqual(result["response"]["state"], "clarification")
                self.assertIsNone(result["response"]["source"])

    def test_corpus_reranks_wrong_intent_with_explicit_topic_evidence(self):
        def wrong_intent(text):
            return {
                "text": text, "service": "PASSPORT", "parent_topic_id": "PASSPORT_GENERAL_INFORMATION",
                "query_topic_id": "PASSPORT_GENERAL_NEW_VS_REISSUE", "is_ood": False,
            }

        result = QueryPipeline(wrong_intent).analyze("passport status check korbo kivabe?")
        self.assertEqual(result["understanding"]["resolved_topic_id"], "PASSPORT_APPLICATION_STATUS")
        self.assertEqual(result["response"]["state"], "answer")
        self.assertEqual(result["response"]["title"], "Track a passport application")

    def test_selection_must_match_a_curated_record(self):
        client = TestClient(create_app(QueryPipeline(fake_predictor)))
        catalog = client.get("/api/guidance")
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(catalog.headers["cache-control"], "no-store")
        self.assertEqual(len(catalog.json()), len(load_records()))
        self.assertEqual(set(catalog.json()[0]), {
            "service", "parent_topic_id", "query_topic_id", "title",
        })
        for body, status in (
            ({"service": "PASSPORT", "parent_topic_id": None, "query_topic_id": "PASSPORT_DOCUMENTS_REQUIRED"}, 404),
            ({"service": "PASSPORT", "parent_topic_id": "PASSPORT_DOCUMENTS", "query_topic_id": "UNKNOWN"}, 404),
            ({"service": "PASSPORT", "parent_topic_id": "PASSPORT_DOCUMENTS", "query_topic_id": None, "text": "extra"}, 400),
            ({"service": [], "parent_topic_id": None, "query_topic_id": None}, 400),
        ):
            with self.subTest(body=body):
                response = client.post("/api/guidance", json=body)
                self.assertEqual(response.status_code, status)
                self.assertIsNone(response.json().get("response"))


class ServerResponsivenessTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_responds_while_inference_runs(self):
        started, release = Event(), Event()

        def slow_predictor(text):
            started.set()
            release.wait(timeout=3)
            return fake_predictor(text)

        async with AsyncClient(
            transport=ASGITransport(app=create_app(QueryPipeline(slow_predictor))),
            base_url="http://test",
        ) as client:
            request = asyncio.create_task(client.post("/api/analyze", json={"text": "NID help"}))
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                start = time.perf_counter()
                status = await asyncio.wait_for(client.get("/api/status"), timeout=1.5)
                self.assertEqual(status.status_code, 200)
                self.assertLess(time.perf_counter() - start, 1.5)
            finally:
                release.set()
                await request


if __name__ == "__main__":
    unittest.main()
