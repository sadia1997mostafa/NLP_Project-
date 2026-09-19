"""Optional local generation must never bypass routing or privacy gates."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.pipeline.service import QueryPipeline
from src.response.local_generator import MODEL_ENV, acceptable_answer, configured_model_path
from src.retrieval.corpus import load_records
from src.retrieval.topic_match import match_topic


class FakeGenerator:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def generate(self, question, record, language):
        self.calls.append((question, record["query_topic_id"], language))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def passport_predictor(_):
    return {
        "service": "PASSPORT", "parent_topic_id": "PASSPORT_STATUS_AND_DELIVERY",
        "query_topic_id": "PASSPORT_APPLICATION_STATUS", "is_ood": False,
    }


class LocalAnswerTests(unittest.TestCase):
    def test_single_default_gguf_is_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            model_dir = Path(directory)
            expected = model_dir / "answer.Q4_K_M.gguf"
            expected.touch()
            with patch.dict(os.environ, {}, clear=True), patch(
                "src.response.local_generator.DEFAULT_MODEL_DIR", model_dir,
            ):
                self.assertEqual(configured_model_path(), expected)

    def test_multiple_default_ggufs_require_an_explicit_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            model_dir = Path(directory)
            (model_dir / "first.gguf").touch()
            (model_dir / "second.gguf").touch()
            with patch.dict(os.environ, {}, clear=True), patch(
                "src.response.local_generator.DEFAULT_MODEL_DIR", model_dir,
            ):
                self.assertIsNone(configured_model_path())

    def test_model_environment_variable_overrides_default(self):
        selected = Path("selected-model.gguf")
        with patch.dict(os.environ, {MODEL_ENV: str(selected)}, clear=True):
            self.assertEqual(configured_model_path(), selected)

    def test_common_banglish_phrases_reach_specific_records(self):
        records = load_records()
        cases = (
            ("amar passport lost hoye geche ki korbo?", "PASSPORT", "PASSPORT_REISSUE_LOST"),
            ("nid dob change korbo kivabe?", "NID", "NID_CORRECTION_DOB"),
        )
        for question, service, expected in cases:
            with self.subTest(question=question):
                match = match_topic(question, service, None, records)
                self.assertIsNotNone(match.record)
                self.assertEqual(match.record["query_topic_id"], expected)

    def test_exact_topic_uses_model_wording_when_acceptable(self):
        writer = FakeGenerator(
            "ই-পাসপোর্টের অবস্থা জানতে Status Check খুলে আবেদন আইডি ও জন্মতারিখ দিন।"
        )
        result = QueryPipeline(predictor=passport_predictor, answer_generator=writer).analyze(
            "passport status check korbo kivabe?"
        )
        self.assertEqual(result["response"]["answer_basis"], "local_finetuned_model")
        self.assertIn("Status Check", result["response"]["body"])
        self.assertEqual(writer.calls[0][1:], ("PASSPORT_APPLICATION_STATUS", "bn"))
        self.assertTrue(result["response"]["source"]["url"].startswith("https://"))

    def test_bad_or_failing_model_falls_back_to_curated_answer(self):
        for answer in (
            "Your passport will arrive in 7 days.",
            "Visit https://unknown.example to check your passport application status.",
            "Check passport status and an officer will deliver it to your home shortly.",
            RuntimeError("model failed"),
        ):
            with self.subTest(answer=answer):
                result = QueryPipeline(
                    predictor=passport_predictor, answer_generator=FakeGenerator(answer),
                ).analyze("How can I check my passport application status?")
                self.assertEqual(result["response"]["answer_basis"], "exact_intent_answer_plan")
                self.assertIn("Status Check", result["response"]["body"])

    def test_generator_never_gets_unmasked_otp(self):
        writer = FakeGenerator("Open Status Check on the official e-Passport portal to see your application status.")
        result = QueryPipeline(predictor=passport_predictor, answer_generator=writer).analyze(
            "My passport status check OTP 123456"
        )
        self.assertNotIn("123456", writer.calls[0][0])
        self.assertNotIn("123456", result["safe_text"])

    def test_unknown_number_is_rejected_even_in_bengali(self):
        record = next(r for r in load_records() if r["query_topic_id"] == "PASSPORT_APPLICATION_STATUS")
        self.assertFalse(acceptable_answer("পাসপোর্টের অবস্থা দেখতে ৭ দিনের মধ্যে আবেদন করুন।", record, "bn"))
        self.assertFalse(acceptable_answer("পাসপোর্টের অবস্থা দেখতে [OTP] লিখুন।", record, "bn"))

    def test_observed_garbage_patterns_are_rejected(self):
        record = next(r for r in load_records() if r["query_topic_id"] == "PASSPORT_APPLICATION_STATUS")
        bad_answers = (
            ("language: bn আবেদন আইডি দিয়ে পাসপোর্টের অবস্থা দেখুন।", "bn"),
            ("Check your application status at taxporat.com before passport delivery.", "en"),
            ("<LMF>আবেদনের অবস্থা যাচাই করুন।</LMF>", "bn"),
            ("limburg: আবেদন আইডি দিয়ে পাসপোর্টের অবস্থা দেখুন।", "bn"),
            ("넹 আবেদন আইডি দিয়ে পাসপোর্টের অবস্থা দেখুন।", "bn"),
            ("Status Check খুলুন। application status check করুন। application status check করুন। application status check করুন।", "bn"),
            ("بچو application status and passport delivery details check کریں۔", "en"),
        )
        for answer, language in bad_answers:
            with self.subTest(answer=answer):
                self.assertFalse(acceptable_answer(answer, record, language))

    def test_emergency_route_never_uses_model(self):
        writer = FakeGenerator("Use the online complaint form for your emergency in Bangladesh.")
        predictor = lambda _: {
            "service": "POLICE_GD", "parent_topic_id": "POLICE_GD_GUIDANCE",
            "query_topic_id": "POLICE_GD_EMERGENCY_ROUTING", "is_ood": False,
        }
        result = QueryPipeline(predictor=predictor, answer_generator=writer).analyze(
            "There is an emergency; should I file an online GD?"
        )
        self.assertEqual(result["response"]["answer_basis"], "exact_intent_answer_plan")
        self.assertIn("999", result["response"]["body"])
        self.assertEqual(writer.calls, [])


if __name__ == "__main__":
    unittest.main()
