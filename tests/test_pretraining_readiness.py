from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import yaml

from src.models.dataset import load_dataset
from src.models.calibrate_ood import select_threshold
from src.models.inference import (
    LocalUnderstandingPipeline,
    UnderstandingPipeline,
    predict_understanding,
)
from src.models.hierarchy import conditioned_label_map, hierarchy_index, only_intent
from src.models.metrics import classification_metrics, ood_metrics
from src.preprocessing.build_label_maps import build
from src.preprocessing.task_views import load_task_view
from src.preprocessing.text_normalization import normalize_text


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = [
    "id", "text", "service", "parent_topic_id", "parent_topic",
    "query_topic_id", "query_topic", "priority", "language_style",
    "privacy_present", "privacy_types", "source_type", "parent_query_id",
    "difficulty", "is_ood", "annotation_notes",
]


class MockTokenizer:
    def __call__(self, text, **kwargs):
        length = kwargs["max_length"]
        return {"input_ids": [min(ord(c), 255) for c in text[:length]] + [0] * max(0, length - len(text)), "attention_mask": [1] * length}


class MockPredictor:
    def __init__(self, label, confidence):
        self.label, self.confidence = label, confidence

    def predict(self, text, top_k=3):
        return {"label": self.label, "confidence": self.confidence, "alternatives": []}


class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all_data = pd.read_csv(ROOT / "data/processed/all_services_canonical_v0_1.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        cls.splits = {
            name: pd.read_csv(ROOT / f"data/splits/{name}.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
            for name in ("train", "dev")
        }

    def test_taxonomy_contract_consistency(self):
        contract = yaml.safe_load((ROOT / "contracts/labels.yaml").read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "frozen")
        self.assertEqual(len(contract["services"]), 6)
        parents = sum((list(s["parent_topics"]) for s in contract["services"].values()), [])
        intents = sum((list(p["query_topics"]) for s in contract["services"].values() for p in s["parent_topics"].values()), [])
        self.assertEqual((len(parents), len(set(parents))), (49, 49))
        self.assertEqual((len(intents), len(set(intents))), (264, 264))

    def test_label_map_reproducibility(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            build(Path(first)); build(Path(second))
            for task, size in {"service": 6, "parent": 49, "intent": 264, "priority": 3}.items():
                a = (Path(first) / f"{task}_labels.json").read_bytes()
                b = (Path(second) / f"{task}_labels.json").read_bytes()
                self.assertEqual(a, b)
                self.assertEqual(len(json.loads(a)["label_to_id"]), size)

    def test_canonical_schema_and_known_labels(self):
        self.assertEqual(list(self.all_data.columns), SCHEMA)
        contract = yaml.safe_load((ROOT / "contracts/labels.yaml").read_text(encoding="utf-8"))
        services = set(contract["services"])
        parents = {p for service in contract["services"].values() for p in service["parent_topics"]}
        intents = {q for service in contract["services"].values() for parent in service["parent_topics"].values() for q in parent["query_topics"]}
        self.assertEqual(set(self.all_data.service), services)
        self.assertFalse(set(self.all_data.parent_topic_id) - parents)
        self.assertFalse(set(self.all_data.query_topic_id) - intents)

    def test_nid_migration_integrity(self):
        inventory = json.loads((ROOT / "data/processed/nid_source_inventory.json").read_text(encoding="utf-8"))
        review = pd.read_csv(ROOT / "data/processed/nid_migration_review.csv")
        nid = self.all_data[self.all_data.service.eq("NID")]
        self.assertEqual(inventory["source_rows"], 0)
        self.assertEqual(len(review), 0)
        self.assertEqual(len(nid), 876)
        self.assertNotIn("REAL", set(nid.source_type))

    def test_train_dev_family_and_exact_text_leakage(self):
        family_sets = {name: set(frame.parent_query_id) for name, frame in self.splits.items()}
        text_sets = {name: set(frame.text.map(normalize_text)) for name, frame in self.splits.items()}
        for left, right in (("train", "dev"),):
            self.assertFalse(family_sets[left] & family_sets[right])
            self.assertFalse(text_sets[left] & text_sets[right])

    def test_text_normalization_determinism(self):
        raw = "  জন্ম   নিবন্ধন\r\nকরব কীভাবে?  "
        self.assertEqual(normalize_text(raw), "জন্ম নিবন্ধন করব কীভাবে?")
        self.assertEqual(normalize_text(raw), normalize_text(raw))

    def test_task_view_and_mock_tokenizer_dataset(self):
        view = load_task_view(ROOT / "data/splits/train.csv", "service")
        self.assertEqual(list(view.columns), ["id", "parent_query_id", "text", "label"])
        labels = {label: index for index, label in enumerate(sorted(view.label.unique()))}
        dataset = load_dataset(ROOT / "data/splits/train.csv", "service", MockTokenizer(), labels, 16)
        self.assertEqual(len(dataset), len(view))
        self.assertEqual(set(dataset[0]), {"input_ids", "attention_mask", "labels"})
        self.assertEqual(len(dataset[0]["input_ids"]), 16)

    def test_parent_conditioned_intent_maps_and_filtering(self):
        services, parent_intents, parent_service = hierarchy_index()
        self.assertEqual(sum(len(parents) for parents in services.values()), 49)
        self.assertEqual(sum(len(intents) for intents in parent_intents.values()), 264)
        for parent, intents in parent_intents.items():
            service = parent_service[parent]
            first = conditioned_label_map("intent", service, parent)
            second = conditioned_label_map("intent", service, parent)
            self.assertEqual(first, second)
            self.assertEqual(set(first), set(intents))
            with self.assertRaises(ValueError):
                conditioned_label_map("intent", next(x for x in services if x != service), parent)
            view = load_task_view(ROOT / "data/splits/train.csv", "intent", service, parent)
            self.assertEqual(set(view.label), set(intents))
            self.assertTrue(view.text.str.startswith(f"[SERVICE={service}] [PARENT={parent}]").all())
        for service, parents in services.items():
            mapping = conditioned_label_map("intent", service)
            self.assertEqual(set(mapping), {intent for parent in parents for intent in parent_intents[parent]})

    def test_single_leaf_routing_and_cli_dry_run(self):
        _, parent_intents, parent_service = hierarchy_index()
        singles = [parent for parent, intents in parent_intents.items() if len(intents) == 1]
        self.assertEqual(len(singles), 5)
        parent = singles[0]
        service = parent_service[parent]
        self.assertEqual(only_intent(service, parent), parent_intents[parent][0])
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.models.train_classifier",
                "--task",
                "intent",
                "--service",
                service,
                "--parent",
                parent,
                "--config",
                str(ROOT / "configs/classifier_intent_small_balanced.yaml"),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("DETERMINISTIC ROUTE", completed.stdout)

    def test_ood_threshold_selection_is_deterministic(self):
        import numpy as np

        labels = np.array([0, 0, 1, 1])
        maximum = np.array([0.9, 0.8, 0.4, 0.3])
        first, candidates = select_threshold(labels, maximum)
        second, _ = select_threshold(labels, maximum)
        self.assertEqual(first, second)
        selected = next(row for row in candidates if row["confidence_threshold"] == first)
        self.assertEqual(selected["balanced_accuracy"], 1.0)

    def test_local_hierarchical_pipeline_schema_with_mocked_models(self):
        def fake_predict(path, text, allowed_labels=None, top_k=3):
            path = str(path)
            if path.endswith("service"):
                label = "NID"
            elif "parent" in path:
                label = "NID_REGISTRATION"
            elif "intent" in path:
                label = allowed_labels[0]
            else:
                label = "Low"
            return {"label": label, "confidence": 0.9, "alternatives": []}

        with patch("src.models.inference._predict_local", side_effect=fake_predict):
            result = LocalUnderstandingPipeline(0.5).predict_understanding(
                "NID registration কীভাবে করব?"
            )
        required = {
            "text", "service", "service_confidence", "service_routing",
            "service_anchor", "service_model_label", "service_model_confidence",
            "parent_topic_id", "parent_topic", "parent_confidence",
            "query_topic_id", "query_topic", "intent_confidence", "intent_routing",
            "priority", "priority_confidence", "priority_routing",
            "is_ood", "ood_score", "overall_confidence", "calibration_status",
            "warnings", "alternatives",
        }
        self.assertEqual(set(result), required)
        self.assertEqual(result["service"], "NID")
        self.assertEqual(result["parent_topic_id"], "NID_REGISTRATION")

    def test_single_leaf_deterministic_routing(self):
        _, parent_intents, parent_service = hierarchy_index()
        singles = [parent for parent, intents in parent_intents.items() if len(intents) == 1]
        self.assertEqual(len(singles), 5)
        for parent in singles:
            self.assertEqual(only_intent(parent_service[parent], parent), parent_intents[parent][0])

    def test_metrics(self):
        result = classification_metrics([0, 0, 1, 1], [0, 1, 1, 1], labels=[0, 1])
        self.assertEqual(result["accuracy"], 0.75)
        self.assertEqual(len(result["confusion_matrix"]), 2)
        ood = ood_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
        self.assertEqual(ood["auroc"], 1.0)

    def test_inference_schema_and_checkpoint_guard(self):
        with patch("src.models.inference.load_default_pipeline", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                predict_understanding("test")
        pipeline = UnderstandingPipeline(
            MockPredictor("NID", 0.9), MockPredictor("NID_REGISTRATION", 0.8),
            MockPredictor("NID_REGISTRATION_PROCESS", 0.7), MockPredictor("Low", 0.6),
        )
        output = predict_understanding("NID কীভাবে করব?", pipeline)
        expected = {"service", "service_confidence", "parent_topic_id", "parent_confidence", "query_topic_id", "query_topic_confidence", "priority", "priority_confidence", "is_ood", "ood_score", "alternatives"}
        self.assertEqual(set(output), expected)


if __name__ == "__main__":
    unittest.main()
