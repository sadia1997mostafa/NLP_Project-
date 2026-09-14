"""DEV-only oracle- and predicted-routing evaluation for Partner A models."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.models.hierarchy import (
    conditioned_label_map,
    contextualize_intent_text,
    global_label_map,
    only_intent,
)
from src.models.metrics import classification_metrics
from src.models.service_anchors import unique_service_anchor


ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "models/final"
DEV = ROOT / "data/splits/dev.csv"
OUTPUT = ROOT / "models/evaluation/hierarchical_dev_metrics.json"
PREDICTIONS = ROOT / "models/evaluation/hierarchical_dev_predictions.csv"
TOKENIZER = ROOT / "models/final/tokenizer_xlm_roberta_base"
PRIORITY_BY_INTENT = ROOT / "configs/priority_by_intent.json"


def predict_batch(
    model_path: Path,
    texts: list[str],
    allowed_labels: list[list[str]] | None = None,
    batch_size: int = 32,
) -> tuple[list[str], list[float]]:
    """Predict one model in batches, optionally masking labels for each row."""
    if not texts:
        return [], []
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_path,
        local_files_only=True,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()
    id_to_label = {int(index): label for index, label in model.config.id2label.items()}
    label_to_id = {label: index for index, label in id_to_label.items()}
    predictions, confidence = [], []
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
            if allowed_labels is not None:
                routed = []
                for offset, probs in enumerate(probabilities):
                    labels = allowed_labels[start + offset]
                    indices = [label_to_id[label] for label in labels]
                    masked = torch.zeros_like(probs)
                    masked[indices] = probs[indices]
                    routed.append(masked / masked.sum().clamp_min(1e-12))
                probabilities = torch.stack(routed)
            values, indices = probabilities.max(dim=-1)
            predictions.extend(id_to_label[int(index)] for index in indices)
            confidence.extend(float(value) for value in values)
    model.to("cpu")
    del model, tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    return predictions, confidence


def assign_grouped(
    frame: pd.DataFrame,
    route_services: pd.Series,
    task: str,
    route_parents: pd.Series | None = None,
    intent_root: Path | None = None,
) -> tuple[pd.Series, pd.Series]:
    predictions = pd.Series(index=frame.index, dtype="object")
    confidences = pd.Series(index=frame.index, dtype="float64")
    for service in sorted(route_services.unique()):
        indices = route_services[route_services.eq(service)].index
        subset = frame.loc[indices]
        if task == "parent":
            labels = list(conditioned_label_map("parent", service))
            predicted, confidence = predict_batch(
                FINAL / "parent" / service,
                subset.text.astype(str).tolist(),
                [labels] * len(subset),
            )
        elif task == "intent":
            if route_parents is None:
                raise ValueError("Intent routing requires parent IDs")
            texts, allowed, deterministic = [], [], {}
            model_indices = []
            for index, text in subset.text.astype(str).items():
                parent = route_parents.loc[index]
                single = only_intent(service, parent)
                if single:
                    deterministic[index] = single
                    continue
                model_indices.append(index)
                texts.append(contextualize_intent_text(text, service, parent))
                allowed.append(list(conditioned_label_map("intent", service, parent)))
            for index, intent in deterministic.items():
                predictions.loc[index] = intent
                confidences.loc[index] = 1.0
            if texts:
                predicted, confidence = predict_batch(
                    (intent_root or (FINAL / "intent")) / service,
                    texts,
                    allowed,
                )
                predictions.loc[model_indices] = predicted
                confidences.loc[model_indices] = confidence
        else:
            raise ValueError(task)
        if task == "parent":
            predictions.loc[indices] = predicted
            confidences.loc[indices] = confidence
    if predictions.isna().any() or confidences.isna().any():
        raise ValueError(f"Incomplete {task} predictions")
    return predictions, confidences


def metric(gold: pd.Series, predicted: pd.Series, task: str) -> dict:
    labels = list(global_label_map(task))
    return classification_metrics(gold, predicted, labels=labels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--intent-root",
        type=Path,
        default=FINAL / "intent",
        help="Directory containing one intent model per service",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help="DEV metrics JSON output path",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=PREDICTIONS,
        help="DEV prediction CSV output path",
    )
    parser.add_argument(
        "--use-service-anchors",
        action="store_true",
        help="Apply frozen conservative lexical service anchors before XLM-R fallback",
    )
    parser.add_argument(
        "--use-deterministic-priority",
        action="store_true",
        help="Derive priority from predicted query_topic_id using the frozen priority contract",
    )
    args = parser.parse_args()

    if DEV.name != "dev.csv":
        raise ValueError("This evaluator is restricted to DEV")
    frame = pd.read_csv(DEV, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    service_pred, service_conf = predict_batch(
        FINAL / "service",
        frame.text.astype(str).tolist(),
    )
    service_pred = pd.Series(service_pred, index=frame.index)
    service_conf = pd.Series(service_conf, index=frame.index)
    service_anchor = pd.Series(
        [unique_service_anchor(text) for text in frame.text.astype(str)],
        index=frame.index,
        dtype="object",
    )

    if args.use_service_anchors:
        anchored = service_anchor.notna()
        service_pred.loc[anchored] = service_anchor.loc[anchored]
        service_conf.loc[anchored] = 1.0

    parent_oracle, parent_oracle_conf = assign_grouped(
        frame,
        frame.service,
        "parent",
    )
    parent_predicted, parent_predicted_conf = assign_grouped(
        frame,
        service_pred,
        "parent",
    )
    intent_oracle, intent_oracle_conf = assign_grouped(
        frame,
        frame.service,
        "intent",
        frame.parent_topic_id,
        intent_root=args.intent_root,
    )
    intent_predicted, intent_predicted_conf = assign_grouped(
        frame,
        service_pred,
        "intent",
        parent_predicted,
        intent_root=args.intent_root,
    )

    if args.use_deterministic_priority:
        priority_map = json.loads(
            PRIORITY_BY_INTENT.read_text(encoding="utf-8")
        )

        missing_intents = sorted(
            set(intent_predicted.astype(str)) - set(priority_map)
        )
        if missing_intents:
            raise ValueError(
                f"Predicted intents missing from priority contract: {missing_intents}"
            )

        priority_pred = intent_predicted.map(priority_map)
        priority_conf = pd.Series(
            1.0,
            index=frame.index,
            dtype="float64",
        )
    else:
        priority_values, priority_confidence = predict_batch(
            FINAL / "priority",
            frame.text.astype(str).tolist(),
        )
        priority_pred = pd.Series(
            priority_values,
            index=frame.index,
            dtype="object",
        )
        priority_conf = pd.Series(
            priority_confidence,
            index=frame.index,
            dtype="float64",
        )

    calibration = json.loads(
        (ROOT / "models/evaluation/ood_dev_calibration.json").read_text(encoding="utf-8")
    )
    threshold = float(calibration["confidence_threshold"])
    ood_decision = service_conf.lt(threshold)
    service_correct = service_pred.eq(frame.service)
    parent_oracle_correct = parent_oracle.eq(frame.parent_topic_id)
    parent_predicted_correct = parent_predicted.eq(frame.parent_topic_id)
    intent_oracle_correct = intent_oracle.eq(frame.query_topic_id)
    intent_predicted_correct = intent_predicted.eq(frame.query_topic_id)
    priority_correct = priority_pred.eq(frame.priority)
    service_parent = service_correct & parent_predicted_correct
    service_parent_intent = service_parent & intent_predicted_correct
    exact = service_parent_intent & priority_correct

    payload = {
        "evaluation_scope": "DEV only",
        "test_data_used": False,
        "rows": len(frame),
        "service_anchor_routing": bool(args.use_service_anchors),
        "service_anchor_unique_rows": int(service_anchor.notna().sum()),
        "deterministic_priority_routing": bool(
            args.use_deterministic_priority
        ),
        "oracle_routing": {
            "definition": "gold service routes parent; gold service and parent route intent",
            "parent": metric(frame.parent_topic_id, parent_oracle, "parent"),
            "intent": metric(frame.query_topic_id, intent_oracle, "intent"),
        },
        "predicted_routing": {
            "service": metric(frame.service, service_pred, "service"),
            "parent": metric(frame.parent_topic_id, parent_predicted, "parent"),
            "intent": metric(frame.query_topic_id, intent_predicted, "intent"),
            "priority": metric(frame.priority, priority_pred, "priority"),
            "service_parent_path_accuracy": float(service_parent.mean()),
            "service_parent_intent_path_accuracy": float(service_parent_intent.mean()),
            "exact_understanding_path_accuracy": float(exact.mean()),
        },
        "ood_on_in_domain_dev": {
            "confidence_threshold": threshold,
            "false_rejection_rate": float(ood_decision.mean()),
            "accepted_rate": float((~ood_decision).mean()),
        },
    }
    output = pd.DataFrame(
        {
            "id": frame.id,
            "gold_service": frame.service,
            "predicted_service": service_pred,
            "service_confidence": service_conf,
            "gold_parent": frame.parent_topic_id,
            "oracle_routed_parent": parent_oracle,
            "oracle_parent_confidence": parent_oracle_conf,
            "predicted_routed_parent": parent_predicted,
            "predicted_parent_confidence": parent_predicted_conf,
            "gold_intent": frame.query_topic_id,
            "oracle_routed_intent": intent_oracle,
            "oracle_intent_confidence": intent_oracle_conf,
            "predicted_routed_intent": intent_predicted,
            "predicted_intent_confidence": intent_predicted_conf,
            "gold_priority": frame.priority,
            "predicted_priority": priority_pred,
            "priority_confidence": priority_conf,
            "service_routing_error": ~service_correct,
            "parent_error_after_oracle_service": ~parent_oracle_correct,
            "parent_error_predicted_route": ~parent_predicted_correct,
            "intent_error_after_oracle_route": ~intent_oracle_correct,
            "intent_error_predicted_route": ~intent_predicted_correct,
            "priority_error": ~priority_correct,
            "is_ood": ood_decision,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.predictions.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    output.to_csv(
        args.predictions,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
    )

    print(json.dumps(payload, indent=2))
    print("SAVED:", args.output, args.predictions)


if __name__ == "__main__":
    main()
