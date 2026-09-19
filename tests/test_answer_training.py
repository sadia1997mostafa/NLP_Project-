"""The generator dataset must stay within reviewed routes and frozen splits."""

import json
import unittest

from scripts.export_answer_training import examples_for_split
from scripts.train_answer_colab import challenge_rows
from src.privacy.detection import detect_privacy
from src.response.model_prompt import prompt_messages
from src.retrieval.lookup import GuidanceLookup


class AnswerTrainingTests(unittest.TestCase):
    def test_export_rejects_official_test_split(self):
        with self.assertRaises(ValueError):
            examples_for_split("test")

    def test_examples_use_all_answer_plans_and_no_identifiers(self):
        records = {
            (record["service"], record["query_topic_id"]): record
            for record in GuidanceLookup().records if record["query_topic_id"]
        }
        for split in ("train", "dev"):
            examples = examples_for_split(split)
            self.assertGreater(len(examples), 100)
            for example in examples:
                with self.subTest(split=split, example=example["prompt"][1]["content"][:40]):
                    self.assertEqual([m["role"] for m in example["prompt"]], ["system", "user"])
                    self.assertEqual(example["completion"][0]["role"], "assistant")
                    payload = json.loads(example["prompt"][1]["content"])
                    record = records[(payload["service"], payload["query_topic_id"])]
                    self.assertEqual(payload["topic"], record["title"])
                    self.assertEqual(payload["service"], record["service"])
                    self.assertFalse(detect_privacy(payload["question"]).privacy_present)
                    self.assertTrue(example["completion"][0]["content"])
                    self.assertTrue(payload["approved_facts"])
                    self.assertEqual(payload["official_source"], record["official_source"])
                    self.assertEqual(payload["source_last_verified"], record["last_verified"])
                    self.assertNotIn("source_url", payload)
                    self.assertNotIn("http", example["completion"][0]["content"].lower())
                    expected = "Bengali" if any(
                        "\u0980" <= char <= "\u09ff" for char in example["completion"][0]["content"]
                    ) else "English"
                    self.assertEqual(payload["required_output_language"], expected)

    def test_training_covers_all_264_routes_in_both_languages(self):
        records = {
            (record["service"], record["query_topic_id"])
            for record in GuidanceLookup().records if record["query_topic_id"]
        }
        rows = examples_for_split("train")
        payloads = [json.loads(row["prompt"][1]["content"]) for row in rows]
        self.assertEqual(len(records), 264)
        self.assertEqual(len(rows), 2112)
        self.assertEqual(len(examples_for_split("dev")), 792)
        for service, topic_id in records:
            languages = {
                payload["required_output_language"] for payload in payloads
                if (payload["service"], payload["query_topic_id"]) == (service, topic_id)
            }
            self.assertEqual(languages, {"Bengali", "English"})

    def test_targets_teach_detailed_but_bounded_answers(self):
        rows = examples_for_split("train")
        by_route = {}
        for row in rows:
            payload = json.loads(row["prompt"][1]["content"])
            if payload["required_output_language"] == "English":
                by_route[payload["query_topic_id"]] = row["completion"][0]["content"]
        self.assertIn("Steps:\n1.", by_route["PASSPORT_APPLICATION_STATUS"])
        self.assertIn("Documents and information:", by_route["PASSPORT_DOCUMENTS_REQUIRED"])
        self.assertIn("Important:", by_route["BR_REGISTRATION_PROCESS"])
        self.assertIn("Important:", by_route["NID_REGISTRATION_ELIGIBILITY"])

        bn_documents = next(
            row["completion"][0]["content"] for row in rows
            if (json.loads(row["prompt"][1]["content"])["query_topic_id"]
                == "PASSPORT_DOCUMENTS_REQUIRED")
            and json.loads(row["prompt"][1]["content"])["required_output_language"] == "Bengali"
        )
        self.assertIn("প্রযোজ্য ক্ষেত্রে মূল NID বা জন্মসনদ", bn_documents)
        self.assertNotIn("Original NID or birth certificate", bn_documents)

    def test_runtime_prompt_matches_export_format(self):
        record = next(
            r for r in GuidanceLookup().records
            if r["query_topic_id"] == "PASSPORT_APPLICATION_STATUS"
        )
        messages = prompt_messages("passport status check korbo kivabe?", record, "bn")
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["required_output_language"], "Bengali")
        self.assertTrue(all(any("\u0980" <= char <= "\u09ff" for char in fact)
                            for fact in payload["approved_facts"]))
        self.assertNotIn("approved_guidance", payload)
        self.assertNotIn("document_conditions", payload)
        self.assertNotIn("source_url", payload)
        self.assertEqual(payload["official_source"], record["official_source"])
        self.assertIn("attaches", payload["source_link_delivery"])

    def test_quality_challenges_are_balanced_private_and_unseen(self):
        challenges = challenge_rows()
        self.assertEqual(len(challenges), 18)
        payloads = [json.loads(row["prompt"][1]["content"]) for row in challenges]
        self.assertEqual(
            {payload["service"] for payload in payloads},
            {"NID", "BIRTH_REGISTRATION", "PASSPORT", "TAX", "POLICE_GD", "DRIVING_LICENCE"},
        )
        self.assertEqual(sum(payload["required_output_language"] == "English" for payload in payloads), 6)
        training_questions = {
            json.loads(row["prompt"][1]["content"])["question"]
            for split in ("train", "dev") for row in examples_for_split(split)
        }
        for payload in payloads:
            self.assertNotIn(payload["question"], training_questions)
            self.assertFalse(detect_privacy(payload["question"]).privacy_present)


if __name__ == "__main__":
    unittest.main()
