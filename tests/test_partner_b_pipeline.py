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
        record = payload["retrieval"]["record"]
        answer = payload["response"]
        self.assertEqual(answer["state"], "answer")
        self.assertEqual(answer["required_documents"], record["required_documents"])
        self.assertGreater(len(answer["required_documents"]), 0)
        self.assertEqual(answer["source"]["url"], record["source_url"])
        self.assertIn('id="document-list"', client.get("/").text)


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
