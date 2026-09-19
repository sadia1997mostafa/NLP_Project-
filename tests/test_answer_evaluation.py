"""The answer test set must stay frozen, complete, private-data-free and held out."""

import json
import unittest

from scripts.evaluate_answer_test import DEFAULT_TEST, load_cases, training_questions, validate_cases
from src.privacy.detection import detect_privacy
from src.preprocessing.text_normalization import normalized_key
from src.response.controller import response_language
from src.retrieval.corpus import load_records


class AnswerEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases(DEFAULT_TEST)

    def test_one_held_out_case_covers_every_exact_topic(self):
        validate_cases(self.cases)
        corpus_topics = {
            record["query_topic_id"] for record in load_records() if record["query_topic_id"]
        }
        self.assertEqual(len(self.cases), 56)
        self.assertEqual({case["query_topic_id"] for case in self.cases}, corpus_topics)

    def test_questions_are_not_in_fine_tuning_train_or_dev(self):
        held_out = {normalized_key(case["question"]) for case in self.cases}
        self.assertFalse(held_out & training_questions())

    def test_questions_are_privacy_clean_and_language_labels_are_correct(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertFalse(detect_privacy(case["question"]).privacy_present)
                self.assertEqual(response_language(case["question"]), case["expected_language"])

    def test_only_emergency_route_expects_controlled_fallback(self):
        fallback_topics = {
            case["query_topic_id"] for case in self.cases
            if case["expected_answer_basis"] == "curated_source_facts"
        }
        self.assertEqual(fallback_topics, {"POLICE_GD_EMERGENCY_ROUTING"})

    def test_jsonl_has_only_expected_fields(self):
        expected = {
            "id", "service", "query_topic_id", "question",
            "expected_language", "expected_answer_basis",
        }
        for line in DEFAULT_TEST.read_text(encoding="utf-8").splitlines():
            self.assertEqual(set(json.loads(line)), expected)


if __name__ == "__main__":
    unittest.main()
