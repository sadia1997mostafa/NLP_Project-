"""Exact intent plans must be complete, grounded, and safely rendered."""

import unittest
from collections import Counter

from src.models.hierarchy import load_contract
from src.response.controller import construct_response
from src.response.local_generator import acceptable_answer
from src.response.model_prompt import SYSTEM_PROMPT, prompt_messages
from src.response.plans import ANSWER_TYPES, GROUNDING_LEVELS, load_answer_plans
from src.retrieval.lookup import GuidanceLookup


class AnswerPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans = load_answer_plans()
        cls.lookup = GuidanceLookup()

    def test_exact_coverage_matches_frozen_contract(self):
        expected = {
            topic_id
            for service in load_contract()["services"].values()
            for parent in service["parent_topics"].values()
            for topic_id in parent["query_topics"]
        }
        self.assertEqual(len(expected), 264)
        self.assertEqual(set(self.plans), expected)

    def test_schema_and_grounding_levels(self):
        levels = Counter()
        for topic_id, plan in self.plans.items():
            with self.subTest(topic=topic_id):
                self.assertIn(plan["grounding_level"], GROUNDING_LEVELS)
                self.assertIn(plan["answer_type"], ANSWER_TYPES)
                self.assertTrue(plan["source_url"].startswith("https://"))
                self.assertIn(".gov.bd", plan["source_url"])
                self.assertEqual(set(plan["direct_answer"]), {"en", "bn"})
                levels[plan["grounding_level"]] += 1
        self.assertEqual(levels["VERIFIED_SPECIFIC"], 56)
        self.assertEqual(sum(levels.values()), 264)

    def test_every_intent_resolves_exactly_without_parent_fallback(self):
        for topic_id, plan in self.plans.items():
            with self.subTest(topic=topic_id):
                result = self.lookup.retrieve({
                    "service": plan["service"],
                    "parent_topic_id": plan["parent_topic_id"],
                    "query_topic_id": topic_id,
                    "is_ood": False,
                })
                self.assertEqual(result["match_level"], "query_topic")
                self.assertEqual(result["record"]["query_topic_id"], topic_id)
                self.assertEqual(result["record"]["answer_plan"], plan)
                response = construct_response(
                    {"response_language": "en"}, result, [], confirmed=True,
                )
                self.assertEqual(response["source"]["url"], plan["source_url"])
                self.assertEqual(response["source"]["name"], plan["official_source"])

    def test_safe_plan_asks_one_specific_clarification(self):
        topic_id = next(
            key for key, plan in self.plans.items()
            if plan["grounding_level"] == "SAFE_CLARIFICATION"
        )
        plan = self.plans[topic_id]
        retrieval = self.lookup.retrieve({
            "service": plan["service"], "parent_topic_id": plan["parent_topic_id"],
            "query_topic_id": topic_id, "is_ood": False,
        })
        response = construct_response(
            {"response_language": "en"}, retrieval, [], confirmed=True,
        )
        self.assertEqual(response["state"], "clarification")
        self.assertEqual(response["grounding_level"], "SAFE_CLARIFICATION")
        self.assertIn(response["clarification_question"], response["body"])
        self.assertIsNotNone(response["source"])

    def test_prompt_makes_qwen_a_writer_not_a_knowledge_source(self):
        record = self.lookup.by_key[(
            "PASSPORT", "PASSPORT_STATUS_AND_DELIVERY", "PASSPORT_APPLICATION_STATUS",
        )]
        messages = prompt_messages("passport status check korbo kivabe?", record, "bn")
        self.assertIn("Use ONLY the approved facts", SYSTEM_PROMPT)
        self.assertIn("conversational Banglish", messages[1]["content"])
        self.assertIn("approved_content", messages[1]["content"])
        self.assertIn("attaches the verified official link separately", SYSTEM_PROMPT)
        self.assertNotIn(record["source_url"], messages[1]["content"])

    def test_safe_paraphrase_passes_but_new_claims_do_not(self):
        record = self.lookup.by_key[(
            "PASSPORT", "PASSPORT_STATUS_AND_DELIVERY", "PASSPORT_APPLICATION_STATUS",
        )]
        paraphrase = (
            "Open Status Check to view your passport application progress, then enter "
            "the application ID and date of birth requested there."
        )
        self.assertTrue(acceptable_answer(paraphrase, record, "en"))
        self.assertFalse(acceptable_answer(
            "Your passport will be approved and delivered in 7 days.", record, "en",
        ))
        self.assertFalse(acceptable_answer(
            "Check it at https://fake.example/passport.", record, "en",
        ))
        self.assertFalse(acceptable_answer(
            "Use [OTP] to check the passport application.", record, "en",
        ))

    def test_banglish_can_pass_without_forcing_bengali_script(self):
        record = self.lookup.by_key[(
            "PASSPORT", "PASSPORT_STATUS_AND_DELIVERY", "PASSPORT_APPLICATION_STATUS",
        )]
        answer = "Passport application status dekhte Status Check open kore application ID din."
        self.assertTrue(acceptable_answer(
            answer, record, "bn", question="passport status check korbo kivabe?",
        ))


if __name__ == "__main__":
    unittest.main()
