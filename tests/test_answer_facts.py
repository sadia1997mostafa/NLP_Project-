"""Every curated route must produce a localized, source-scoped answer."""

import unittest

from src.response.controller import construct_response
from src.response.facts import facts_for, load_factbook, render_fact, route_key
from src.retrieval.corpus import load_records


class AnswerFactsTests(unittest.TestCase):
    def test_factbook_covers_every_curated_route(self):
        records = load_records()
        self.assertEqual(len(records), 67)
        self.assertEqual(set(load_factbook()), {route_key(record) for record in records})

    def test_every_route_renders_in_both_languages_without_pasting_guidance(self):
        for record in load_records():
            for language in ("en", "bn"):
                with self.subTest(route=route_key(record), language=language):
                    retrieval = {"status": "match", "match_level": "query_topic", "record": record}
                    response = construct_response(
                        {"response_language": language}, retrieval, [], confirmed=True,
                    )
                    self.assertEqual(response["state"], "answer")
                    self.assertEqual(response["answer_basis"], "curated_source_facts")
                    self.assertEqual(response["source"]["url"], record["source_url"])
                    self.assertEqual(response["required_documents"], record["required_documents"])
                    self.assertTrue(response["body"].strip())
                    self.assertNotIn(record["guidance"], " ".join([response["body"], *response["steps"]]))
                    units = facts_for(record)
                    self.assertIn(render_fact(units[0], language), response["body"])
                    if language == "bn":
                        self.assertRegex(response["body"], "[\u0980-\u09ff]")

    def test_emergency_warning_is_in_lead_in_both_languages(self):
        record = next(
            record for record in load_records()
            if route_key(record) == "POLICE_GD_EMERGENCY_ROUTING"
        )
        for language, warning in (("en", "cannot dispatch"), ("bn", "সাহায্য পাঠাতে পারে না")):
            with self.subTest(language=language):
                response = construct_response(
                    {"response_language": language},
                    {"status": "match", "match_level": "query_topic", "record": record},
                    [], confirmed=True,
                )
                self.assertIn(warning, response["body"])
                self.assertEqual(response["steps"], [])

    def test_conditioned_examples_remain_conditioned(self):
        examples = {
            "NID_CORRECTION_DOB": "Others must follow",
            "PASSPORT_DOCUMENTS_MINOR_APPLICANT": "If the applicant is under 18",
            "POLICE_GD_COPY_DOWNLOAD": "If the complaint has been accepted",
        }
        for record in load_records():
            key = route_key(record)
            if key in examples:
                with self.subTest(route=key):
                    rendered = " ".join(render_fact(unit, "en") for unit in facts_for(record))
                    self.assertIn(examples[key], rendered)


if __name__ == "__main__":
    unittest.main()
