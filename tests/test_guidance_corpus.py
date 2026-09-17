"""Check every curated record against the frozen routing contract."""

import json
import tempfile
import unittest
from pathlib import Path

from src.retrieval.corpus import load_records


class GuidanceCorpusTests(unittest.TestCase):
    def test_all_services_have_general_guidance(self):
        records = load_records()
        general = {item["service"] for item in records if item["parent_topic_id"] is None}
        self.assertEqual(general, {"NID", "BIRTH_REGISTRATION", "PASSPORT", "TAX", "POLICE_GD", "DRIVING_LICENCE"})
        self.assertEqual(len(records), 14)

    def test_rejects_unknown_topic_and_unofficial_source(self):
        records = load_records()
        for field, value in (("query_topic_id", "UNKNOWN"), ("source_url", "https://example.com/")):
            changed = json.loads(json.dumps(records))
            changed[-1][field] = value
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "guidance.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_records(path)


if __name__ == "__main__":
    unittest.main()
