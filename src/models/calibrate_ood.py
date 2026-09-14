"""Calibrate a simple maximum-softmax OOD threshold using DEV data only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import balanced_accuracy_score, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.models.metrics import ood_metrics
from src.models.service_anchors import unique_service_anchor


ROOT = Path(__file__).resolve().parents[2]
IN_DOMAIN = ROOT / "data/splits/dev.csv"
OOD = ROOT / "data/splits/ood_dev.csv"
MODEL = ROOT / "models/final/service"
TOKENIZER = ROOT / "models/final/tokenizer_xlm_roberta_base"
OUTPUT = ROOT / "models/evaluation/ood_dev_calibration.json"
SCORES = ROOT / "models/evaluation/ood_dev_scores.csv"


def confidence_scores(texts: list[str], batch_size: int = 32) -> dict[str, list[float]]:
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL, local_files_only=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()
    maximum, entropy, margin = [], [], []
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            encoded = tokenizer(
                texts[start : start + batch_size],
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            probabilities = torch.softmax(
                model(**{key: value.to(device) for key, value in encoded.items()}).logits,
                dim=-1,
            ).cpu()
            values = probabilities.topk(2, dim=-1).values
            maximum.extend(values[:, 0].tolist())
            margin.extend((values[:, 0] - values[:, 1]).tolist())
            entropy.extend(
                (-(probabilities * probabilities.clamp_min(1e-12).log()).sum(dim=-1)).tolist()
            )
    return {"maximum_softmax": maximum, "entropy": entropy, "margin": margin}


def select_threshold(labels: np.ndarray, maximum: np.ndarray) -> tuple[float, list[dict]]:
    """Select the DEV threshold maximizing OOD-vs-ID balanced accuracy."""
    candidates = np.round(np.arange(0.05, 0.951, 0.01), 2)
    rows = []
    for threshold in candidates:
        predicted_ood = maximum < threshold
        in_domain = labels == 0
        ood = labels == 1
        rows.append(
            {
                "confidence_threshold": float(threshold),
                "balanced_accuracy": float(balanced_accuracy_score(labels, predicted_ood)),
                "ood_f1": float(f1_score(labels, predicted_ood, zero_division=0)),
                "in_domain_acceptance_rate": float((~predicted_ood[in_domain]).mean()),
                "ood_rejection_rate": float(predicted_ood[ood].mean()),
                "false_rejection_rate": float(predicted_ood[in_domain].mean()),
                "false_acceptance_rate": float((~predicted_ood[ood]).mean()),
            }
        )
    # Deterministic DEV-only rule: highest balanced accuracy, then lowest false
    # acceptance, then lowest threshold (more conservative about rejecting ID).
    best = max(
        rows,
        key=lambda row: (
            row["balanced_accuracy"],
            -row["false_acceptance_rate"],
            -row["confidence_threshold"],
        ),
    )
    return best["confidence_threshold"], rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    if IN_DOMAIN.name != "dev.csv" or OOD.name != "ood_dev.csv":
        raise ValueError("Calibration is restricted to in-domain DEV and OOD DEV")
    in_domain = pd.read_csv(IN_DOMAIN, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    ood = pd.read_csv(OOD, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    combined = pd.concat(
        [
            pd.DataFrame({"id": in_domain["id"], "text": in_domain["text"], "source": "in_domain_dev", "is_ood": 0}),
            pd.DataFrame({"id": ood["id"], "text": ood["text"], "source": "ood_dev", "is_ood": 1}),
        ],
        ignore_index=True,
    )
    scores = confidence_scores(combined.text.astype(str).tolist(), args.batch_size)
    for key, values in scores.items():
        combined[key] = values

    combined["service_anchor"] = combined.text.astype(str).map(unique_service_anchor)
    combined["trusted_anchor_for_ood"] = (
        combined.service_anchor.notna()
        & combined.service_anchor.ne("TAX")
    )
    combined["routing_confidence"] = combined["maximum_softmax"]
    combined.loc[combined.trusted_anchor_for_ood, "routing_confidence"] = 1.0

    combined["ood_score"] = 1.0 - combined["routing_confidence"]
    labels = combined.is_ood.to_numpy(dtype=int)
    maximum = combined.routing_confidence.to_numpy(dtype=float)
    threshold, candidates = select_threshold(labels, maximum)
    selected = next(
        row for row in candidates if row["confidence_threshold"] == threshold
    )
    combined["accepted"] = combined.routing_confidence.ge(threshold)
    discrimination = ood_metrics(labels, combined.ood_score.to_numpy(dtype=float))
    payload = {
        "method": "anchor_aware_service_routing_confidence",
        "calibration_status": "provisional_synthetic_dev_only",
        "selection_rule": (
            "maximize DEV balanced accuracy; tie-break by lower false acceptance, "
            "then lower threshold"
        ),
        "test_data_used": False,
        "data": {
            "in_domain": "data/splits/dev.csv",
            "in_domain_rows": int((labels == 0).sum()),
            "ood": "data/splits/ood_dev.csv",
            "ood_rows": int((labels == 1).sum()),
        },
        "confidence_threshold": threshold,
        "ood_score_definition": "1 - routing_confidence; routing_confidence=1.0 for unique non-TAX trusted anchors, otherwise service-model maximum softmax",
        "selected_metrics": selected,
        "discrimination": discrimination,
        "threshold_candidates": candidates,
        "limitations": [
            "Threshold is calibrated on synthetic DEV data only.",
            "The service-model maximum softmax score is a simple baseline, not a safety guarantee.",
            "Unique TAX anchors are not auto-accepted for OOD because DEV OOD contains holding-tax collisions.",
            "Trusted lexical anchors were selected/calibrated on DEV only and require later real-world validation.",
            "No test or OOD-test data was used.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    combined.drop(columns=["text"]).to_csv(
        SCORES,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
    )
    print(json.dumps({key: payload[key] for key in (
        "method", "calibration_status", "data", "confidence_threshold",
        "selected_metrics", "discrimination",
    )}, indent=2))
    print("SAVED:", OUTPUT, SCORES)


if __name__ == "__main__":
    main()
