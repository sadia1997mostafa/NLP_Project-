"""Privacy and backend contract tests that do not require model artifacts."""

import unittest

from fastapi.testclient import TestClient

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


if __name__ == "__main__":
    unittest.main()
