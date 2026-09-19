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
from src.response.plans import load_answer_plans


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

    def test_masks_unseparated_otp_and_bengali_digits(self):
        for text, expected in (
            ("OTP 123456", "OTP [OTP]"),
            ("ওটিপি ১২৩৪৫৬", "ওটিপি [OTP]"),
        ):
            with self.subTest(text=text):
                result = detect_privacy(text)
                self.assertEqual(result.safe_text, expected)
                self.assertEqual(result.privacy_types, ["otp"])
        self.assertFalse(detect_privacy("OTP ashtese na").privacy_present)

    def test_masks_banglish_personal_fields(self):
        result = detect_privacy("amar nam: Ayesha Rahman, amar thikana: 12 Lake Road; NID correction")
        self.assertNotIn("Ayesha Rahman", result.safe_text)
        self.assertNotIn("12 Lake Road", result.safe_text)
        self.assertIn("NID correction", result.safe_text)

    def test_explicit_service_identifiers_use_the_correct_privacy_type(self):
        cases = (
            ("amar birth certificate no 54575477 hariye geche", "birth_registration", "[BIRTH_REGISTRATION]"),
            ("amr passport no 1234567890", "passport", "[PASSPORT]"),
            ("e-TIN no 123456789012", "tin", "[TIN]"),
            ("driving licence no DHA-1234567", "driving_licence", "[DRIVING_LICENCE]"),
            ("application ID 1234-5678", "application_id", "[APPLICATION_ID]"),
            ("জন্ম নিবন্ধন নম্বর ১২৩৪৫৬৭৮", "birth_registration", "[BIRTH_REGISTRATION]"),
        )
        for text, expected_type, placeholder in cases:
            with self.subTest(text=text):
                result = detect_privacy(text)
                self.assertEqual(result.privacy_types, [expected_type])
                self.assertIn(placeholder, result.safe_text)

    def test_explicit_passport_number_wins_over_generic_nid_length(self):
        result = detect_privacy("passport no 1234567890")
        self.assertEqual(result.safe_text, "passport no [PASSPORT]")
        self.assertEqual(result.privacy_types, ["passport"])

    def test_explicit_address_masks_contained_phone_as_well(self):
        result = detect_privacy("address: 12 Lake Road phone 01712345678; passport renewal")
        self.assertNotIn("Lake Road", result.safe_text)
        self.assertNotIn("01712345678", result.safe_text)
        self.assertIn("passport renewal", result.safe_text)
        self.assertIn("address", result.privacy_types)

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
        invalid = client.post("/api/analyze", json={"text": " "})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.headers["cache-control"], "no-store")

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
        self.assertGreater(result["understanding"]["topic_match_score"], 0.25)
        self.assertGreaterEqual(result["understanding"]["topic_match_margin"], 0.06)
        self.assertEqual(result["response"]["state"], "answer")
        self.assertEqual(result["response"]["title"], "Track a passport application")

    def test_bengali_service_correction_keeps_model_route_for_audit(self):
        def wrong_service(text):
            return {
                "text": text, "service": "TAX", "parent_topic_id": "TAX_TIN_SERVICES",
                "query_topic_id": "TAX_TIN_CANCELLATION", "is_ood": False,
            }

        result = QueryPipeline(wrong_service).analyze("আমার এনআইডি সংশোধন করবো কীভাবে?")
        self.assertEqual(result["understanding"]["model_service"], "TAX")
        self.assertEqual(result["understanding"]["service"], "NID")
        self.assertEqual(result["understanding"]["resolved_parent_id"], "NID_CORRECTION")
        self.assertNotIn("resolved_topic_id", result["understanding"])
        self.assertEqual(result["response"]["match_level"], "parent_topic")

    def test_bengali_topic_matching_and_qualifier_guard(self):
        def predict(text):
            return {
                "text": text, "service": "BIRTH_REGISTRATION",
                "parent_topic_id": "BR_REGISTRATION", "query_topic_id": "BR_REGISTRATION_PROCESS",
                "is_ood": False,
            }

        result = QueryPipeline(predict).analyze("জন্ম নিবন্ধন যাচাই করতে চাই")
        self.assertEqual(result["understanding"]["resolved_topic_id"], "BR_VERIFICATION_RECORD")
        self.assertEqual(result["response"]["match_level"], "query_topic")

        def learner_predict(text):
            return {
                "text": text, "service": "DRIVING_LICENCE",
                "parent_topic_id": "DRIVING_LICENCE_LEARNER",
                "query_topic_id": "DRIVING_LICENCE_LEARNER_DOCUMENTS", "is_ood": False,
            }

        generic = QueryPipeline(learner_predict).analyze("ড্রাইভিং লাইসেন্সের কাগজপত্র কী লাগবে?")
        self.assertNotEqual(generic["response"]["match_level"], "query_topic")

    def test_bengali_answer_and_privacy_notice(self):
        def predict(text):
            return {
                "text": text, "service": "NID", "parent_topic_id": "NID_CORRECTION",
                "query_topic_id": "NID_CORRECTION_DOB", "is_ood": False,
            }

        result = QueryPipeline(predict).analyze("এনআইডি সংশোধন করবো, ফোন 01712345678")
        self.assertTrue(result["privacy_present"])
        self.assertNotIn("01712345678", str(result))
        self.assertEqual(result["response"]["language"], "bn")
        self.assertIn("ব্যক্তিগত", result["warnings"][0])

    def test_topic_specific_words_prevent_service_overlap_errors(self):
        cases = (
            ("BIRTH_REGISTRATION", "Birth certificate correction of mother's name", "BR_CORRECTION_PROCESS"),
            ("PASSPORT", "passport fee koto?", "PASSPORT_FEES_INFORMATION"),
            ("PASSPORT", "passport delivery status check", "PASSPORT_APPLICATION_STATUS"),
            ("DRIVING_LICENCE", "Driving licence renewal fee koto?", "DRIVING_LICENCE_FEE_INFORMATION"),
            ("BIRTH_REGISTRATION", "জন্ম নিবন্ধনের আবেদন অবস্থা দেখব কীভাবে?", "BR_APPLICATION_STATUS"),
        )
        for service, query, expected in cases:
            with self.subTest(query=query):
                def wrong_topic(text):
                    return {
                        "text": text, "service": service, "parent_topic_id": "WRONG",
                        "query_topic_id": "WRONG", "is_ood": False,
                    }

                result = QueryPipeline(wrong_topic).analyze(query)
                self.assertEqual(result["understanding"]["resolved_topic_id"], expected)
                self.assertEqual(result["response"]["match_level"], "query_topic")

    def test_selection_must_match_a_curated_record(self):
        client = TestClient(create_app(QueryPipeline(fake_predictor)))
        catalog = client.get("/api/guidance")
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(catalog.headers["cache-control"], "no-store")
        fallback_records = sum(
            record["query_topic_id"] is None for record in load_records()
        )
        self.assertEqual(
            len(catalog.json()),
            len(load_answer_plans()) + fallback_records,
        )
        self.assertEqual(set(catalog.json()[0]), {
            "service", "parent_topic_id", "query_topic_id", "title",
        })
        for body, status in (
            ({"service": "PASSPORT", "parent_topic_id": None, "query_topic_id": "PASSPORT_DOCUMENTS_REQUIRED"}, 404),
            ({"service": "PASSPORT", "parent_topic_id": "PASSPORT_DOCUMENTS", "query_topic_id": "UNKNOWN"}, 404),
            ({"service": "PASSPORT", "parent_topic_id": "PASSPORT_DOCUMENTS", "query_topic_id": None, "text": "extra"}, 400),
            ({"service": [], "parent_topic_id": None, "query_topic_id": None}, 400),
            ({"service": "NID", "parent_topic_id": None, "query_topic_id": None, "language": "xx"}, 400),
        ):
            with self.subTest(body=body):
                response = client.post("/api/guidance", json=body)
                self.assertEqual(response.status_code, status)
                self.assertIsNone(response.json().get("response"))

        localized = client.post("/api/guidance", json={
            "service": "NID", "parent_topic_id": None, "query_topic_id": None,
            "language": "bn",
        })
        self.assertEqual(localized.status_code, 200)
        self.assertEqual(localized.json()["response"]["language"], "bn")


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
