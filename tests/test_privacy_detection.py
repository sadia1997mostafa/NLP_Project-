"""Regression coverage for multilingual, context-aware privacy masking."""

import json
import unittest
from pathlib import Path

from src.privacy.detection import detect_privacy


CASES = Path(__file__).resolve().parents[1] / "data" / "privacy" / "privacy_cases.jsonl"


class PrivacyCorpusTests(unittest.TestCase):
    def test_every_privacy_case_matches_the_expected_contract(self):
        rows = [
            json.loads(line)
            for line in CASES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(rows), 100)
        self.assertEqual(sum(row["privacy_present"] for row in rows), 65)
        self.assertEqual(sum(not row["privacy_present"] for row in rows), 35)
        self.assertGreaterEqual(sum(len(row["types"]) > 1 for row in rows), 12)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        for row in rows:
            with self.subTest(case=row["id"]):
                result = detect_privacy(row["text"])
                self.assertEqual(result.privacy_present, row["privacy_present"])
                self.assertEqual(result.privacy_types, row["types"])
                self.assertEqual(result.safe_text, row["safe_text"])

    def test_masking_preserves_service_and_intent_words(self):
        rows = [
            json.loads(line)
            for line in CASES.read_text(encoding="utf-8").splitlines()
            if line.strip() and line.startswith('{"id":"P')
        ]
        for row in rows:
            with self.subTest(case=row["id"]):
                result = detect_privacy(row["text"])
                for word in ("NID", "passport", "জন্ম নিবন্ধন", "correction", "status", "renew"):
                    if word.casefold() in row["text"].casefold():
                        self.assertIn(word.casefold(), result.safe_text.casefold())


if __name__ == "__main__":
    unittest.main()
