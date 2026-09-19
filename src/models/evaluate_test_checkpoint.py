"""TEST-only evaluation for frozen service, parent, intent, and priority checkpoints."""

from __future__ import annotations

import argparse
import gc
import json
import math
from pathlib import Path

import pandas as pd

from src.models.hierarchy import conditioned_label_map, contextualize_intent_text, hierarchy_index
from src.models.metrics import classification_metrics
from src.preprocessing.task_views import TASK_TARGETS


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TOKENIZER = ROOT / "models" / "final" / "tokenizer_xlm_roberta_base"


def evaluate(
    checkpoint: Path,
    task: str,
    predictions_path: Path,
    metrics_path: Path,
    service: str | None = None,
    parent: str | None = None,
    data_path: Path | None = None,
    tokenizer_path: Path = DEFAULT_TOKENIZER,
) -> dict:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if data_path is None:
        data_path = ROOT / "data" / "splits" / "test.csv"
    if data_path.name != "test.csv":
        raise ValueError("This evaluator is deliberately restricted to test.csv")
    frame = pd.read_csv(data_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if service:
        frame = frame[frame["service"] == service]
    if parent:
        frame = frame[frame["parent_topic_id"] == parent]
    if frame.empty:
        raise ValueError("No TEST rows matched the requested scope")

    label_map = conditioned_label_map(task, service, parent)
    label_order = list(label_map)
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint, local_files_only=True)
    if model.config.num_labels != len(label_order):
        raise ValueError(f"Checkpoint has {model.config.num_labels} labels; expected {len(label_order)}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()

    predicted: list[str] = []
    confidence: list[float] = []
    top2_label: list[str] = []
    top2_confidence: list[float] = []
    entropy: list[float] = []
    margin: list[float] = []
    texts = frame["text"].astype(str).tolist()
    if task == "intent":
        texts = [
            contextualize_intent_text(text, row.service, row.parent_topic_id)
            for text, row in zip(texts, frame[["service", "parent_topic_id"]].itertuples(index=False))
        ]
    _, parent_to_intents, _ = hierarchy_index()
    with torch.inference_mode():
        for start in range(0, len(texts), 32):
            encoded = tokenizer(texts[start:start + 32], padding=True, truncation=True, max_length=128, return_tensors="pt")
            probabilities = torch.softmax(model(**{k: v.to(device) for k, v in encoded.items()}).logits, dim=-1).cpu()
            batch_rows = frame.iloc[start:start + len(probabilities)]
            routed = []
            for probs, (_, row) in zip(probabilities, batch_rows.iterrows()):
                if task == "intent" and parent is None:
                    valid = [label_map[label] for label in parent_to_intents[row["parent_topic_id"]]]
                    masked = torch.zeros_like(probs)
                    masked[valid] = probs[valid]
                    probs = masked / masked.sum().clamp_min(1e-12)
                routed.append(probs)
            probabilities = torch.stack(routed)
            values, indices = probabilities.topk(min(2, len(label_order)), dim=-1)
            for probs, vals, ids in zip(probabilities, values, indices):
                predicted.append(label_order[int(ids[0])])
                confidence.append(float(vals[0]))
                if len(label_order) > 1:
                    top2_label.append(label_order[int(ids[1])])
                    top2_confidence.append(float(vals[1]))
                    margin.append(float(vals[0] - vals[1]))
                else:
                    top2_label.append("")
                    top2_confidence.append(0.0)
                    margin.append(1.0)
                entropy.append(float(-(probs * probs.clamp_min(1e-12).log()).sum()))

    gold = frame[TASK_TARGETS[task]].tolist()
    result = classification_metrics(gold, predicted, labels=label_order)
    result.update({
        "task": task,
        "service": service,
        "parent_topic_id": parent,
        "checkpoint": str(checkpoint.relative_to(ROOT) if checkpoint.is_relative_to(ROOT) else checkpoint),
        "device": str(device),
        "rows": len(frame),
        "label_order": label_order,
        "routing": "gold_parent_masked" if task == "intent" and parent is None else "scope_only",
    })
    output = pd.DataFrame({
        "id": frame["id"].tolist(),
        "gold_label": gold,
        "predicted_label": predicted,
        "confidence": confidence,
        "top2_label": top2_label,
        "top2_confidence": top2_confidence,
        "margin": margin,
        "entropy": entropy,
        "parent_topic_id": frame["parent_topic_id"].tolist(),
    })
    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(predictions_path, index=False, encoding="utf-8", lineterminator="\n")
    metrics_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    model.to("cpu")
    del model, tokenizer, probabilities
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--task", choices=["service", "parent", "intent", "priority"], required=True)
    parser.add_argument("--service")
    parser.add_argument("--parent")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZER)
    args = parser.parse_args()
    result = evaluate(args.checkpoint.resolve(), args.task, args.predictions, args.metrics, args.service, args.parent, tokenizer_path=args.tokenizer.resolve())
    print(f"DEVICE: {result['device']}")
    print(f"ROWS: {result['rows']}")
    print(f"ACCURACY: {result['accuracy']:.10f}")
    print(f"MACRO F1: {result['macro_f1']:.10f}")
    print("LABEL ORDER:", result["label_order"])
    print("SAVED:", args.predictions, args.metrics)


if __name__ == "__main__":
    main()
