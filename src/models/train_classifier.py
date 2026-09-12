"""Configurable Hugging Face classifier entry point. Training is opt-in."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.models.dataset import load_dataset
from src.models.metrics import classification_metrics


ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path, task: str) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if task not in config["tasks"]:
        raise ValueError(f"Task {task!r} missing from config")
    merged = dict(config["training"])
    merged.update(config["tasks"][task])
    return merged


def load_map(task: str, service: str | None = None) -> dict:
    path = ROOT / "contracts" / "label_maps" / f"{task}_labels.json"
    full_map = json.loads(path.read_text(encoding="utf-8"))["label_to_id"]
    if service is None:
        return full_map
    if task != "parent":
        raise ValueError("--service is currently supported only with --task parent")
    frame = pd.read_csv(ROOT / "data" / "splits" / "train.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    labels = set(frame.loc[frame["service"] == service, "parent_topic_id"])
    if not labels:
        raise ValueError(f"No parent labels found for service {service!r}")
    unknown = sorted(labels - set(full_map))
    if unknown:
        raise ValueError(f"Unknown parent labels for {service}: {unknown}")
    ordered = sorted(labels, key=lambda label: full_map[label])
    return {label: index for index, label in enumerate(ordered)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["service", "parent", "intent", "priority"], required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "classifier_base.yaml")
    parser.add_argument("--service", help="Restrict parent-topic training to one service (hierarchical mode)")
    parser.add_argument(
        "--execute-training",
        action="store_true",
        help="Explicitly authorize the future fine-tuning run (not used during preparation)",
    )
    args = parser.parse_args()
    if args.service and args.task != "parent":
        parser.error("--service is currently supported only with --task parent")
    if args.service and args.service not in load_map("service"):
        parser.error(f"Unknown service {args.service!r}")
    config = load_config(args.config, args.task)
    label_map = load_map(args.task, args.service)
    if args.service is None and len(label_map) != int(config["num_labels"]):
        raise ValueError("num_labels does not match the frozen label map")
    scope = f"; service: {args.service}" if args.service else ""
    print(f"Task: {args.task}{scope}; labels: {len(label_map)}; model: {config['model_name']}")
    if not args.execute_training:
        print("DRY RUN ONLY: configuration and label map validated; no model loaded or trained.")
        return

    try:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            EarlyStoppingCallback,
            Trainer,
            TrainingArguments,
            set_seed,
        )
    except ImportError as exc:
        raise RuntimeError("Install requirements-training.txt before training") from exc

    set_seed(int(config["seed"]))
    tokenizer = AutoTokenizer.from_pretrained(config["tokenizer_name"])
    train = load_dataset(ROOT / "data" / "splits" / "train.csv", args.task, tokenizer, label_map, config["max_length"], service=args.service)
    dev = load_dataset(ROOT / "data" / "splits" / "dev.csv", args.task, tokenizer, label_map, config["max_length"], service=args.service)
    model = AutoModelForSequenceClassification.from_pretrained(
        config["model_name"], num_labels=len(label_map), id2label={v: k for k, v in label_map.items()}, label2id=label_map
    )
    output_dir = ROOT / config["output_path"].format(task=args.task)
    if args.service:
        output_dir = output_dir / args.service
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        seed=int(config["seed"]),
        per_device_train_batch_size=int(config["train_batch_size"]),
        per_device_eval_batch_size=int(config["evaluation_batch_size"]),
        learning_rate=float(config["learning_rate"]),
        num_train_epochs=float(config["epochs"]),
        weight_decay=float(config["weight_decay"]),
        warmup_ratio=float(config["warmup_ratio"]),
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=int(config.get("save_total_limit", 2)),
        save_only_model=bool(config.get("save_only_model", True)),
        load_best_model_at_end=True,
        metric_for_best_model="eval_macro_f1",
        greater_is_better=True,
    )
    trainer_class = Trainer
    trainer_kwargs = {}
    if config.get("class_weighting") == "balanced":
        import torch
        counts = np.bincount([label_map[label] for label in train.labels], minlength=len(label_map))
        weights = len(train) / (len(label_map) * np.maximum(counts, 1))

        class WeightedTrainer(Trainer):
            def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
                labels = inputs.pop("labels")
                outputs = model(**inputs)
                loss = torch.nn.functional.cross_entropy(
                    outputs.logits, labels, weight=torch.tensor(weights, device=outputs.logits.device, dtype=outputs.logits.dtype)
                )
                return (loss, outputs) if return_outputs else loss

        trainer_class = WeightedTrainer

    def compute_metrics(prediction):
        predicted = np.argmax(prediction.predictions, axis=-1)
        return {key: value for key, value in classification_metrics(prediction.label_ids, predicted).items() if key != "confusion_matrix"}

    trainer = trainer_class(
        model=model,
        args=training_args,
        train_dataset=train,
        eval_dataset=dev,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=int(config["early_stopping_patience"]))],
        **trainer_kwargs,
    )
    trainer.train()


if __name__ == "__main__":
    main()
