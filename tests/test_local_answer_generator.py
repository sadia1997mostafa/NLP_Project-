"""Optional local generation must never bypass routing or privacy gates."""

import unittest

from src.pipeline.service import QueryPipeline
from src.response.local_generator import acceptable_answer
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
            RuntimeError("model failed"),
        ):
            with self.subTest(answer=answer):
                result = QueryPipeline(
                    predictor=passport_predictor, answer_generator=FakeGenerator(answer),
                ).analyze("How can I check my passport application status?")
                self.assertEqual(result["response"]["answer_basis"], "curated_source_facts")
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

    def test_emergency_route_never_uses_model(self):
        writer = FakeGenerator("Use the online complaint form for your emergency in Bangladesh.")
        predictor = lambda _: {
            "service": "POLICE_GD", "parent_topic_id": "POLICE_GD_GUIDANCE",
            "query_topic_id": "POLICE_GD_EMERGENCY_ROUTING", "is_ood": False,
        }
        result = QueryPipeline(predictor=predictor, answer_generator=writer).analyze(
            "There is an emergency; should I file an online GD?"
        )
        self.assertEqual(result["response"]["answer_basis"], "curated_source_facts")
        self.assertIn("999", result["response"]["body"])
        self.assertEqual(writer.calls, [])


if __name__ == "__main__":
    unittest.main()
