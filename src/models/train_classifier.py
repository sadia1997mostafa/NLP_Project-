"""Configurable Hugging Face classifier entry point. Training is opt-in."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.models.dataset import load_dataset
from src.models.hierarchy import conditioned_label_map, global_label_map
from src.models.metrics import classification_metrics


ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path, task: str) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if task not in config["tasks"]:
        raise ValueError(f"Task {task!r} missing from config")
    merged = dict(config["training"])
    merged.update(config["tasks"][task])
    return merged


def load_map(task: str, service: str | None = None, parent: str | None = None) -> dict:
    if task in {"service", "priority"}:
        return conditioned_label_map(task)
    return conditioned_label_map(task, service, parent)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["service", "parent", "intent", "priority"], required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "classifier_base.yaml")
    parser.add_argument("--service", help="Service scope for hierarchical parent/intent training")
    parser.add_argument("--parent", help="Parent scope for hierarchical intent training")
    parser.add_argument(
        "--execute-training",
        action="store_true",
        help="Explicitly authorize the future fine-tuning run (not used during preparation)",
    )
    args = parser.parse_args()
    if args.task == "parent" and (not args.service or args.parent):
        parser.error("--task parent requires --service and does not accept --parent")
    if args.task == "intent" and not args.service:
        parser.error("--task intent requires --service; --parent is optional for a diagnostic parent-only run")
    if args.task in {"service", "priority"} and (args.service or args.parent):
        parser.error(f"--task {args.task} does not accept --service/--parent")
    config = load_config(args.config, args.task)
    label_map = load_map(args.task, args.service, args.parent)
    if args.task in {"service", "priority"} and len(label_map) != int(config["num_labels"]):
        raise ValueError("num_labels does not match the frozen label map")
    scope = f"; service: {args.service}" if args.service else ""
    scope += f"; parent: {args.parent}" if args.parent else ""
    print(f"Task: {args.task}{scope}; labels: {len(label_map)}; model: {config['model_name']}")
    if args.task == "intent" and args.parent and len(label_map) == 1:
        print(f"DETERMINISTIC ROUTE: {next(iter(label_map))}; classifier training is unnecessary.")
        return
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
    train = load_dataset(ROOT / "data" / "splits" / "train.csv", args.task, tokenizer, label_map, config["max_length"], service=args.service, parent=args.parent)
    dev = load_dataset(ROOT / "data" / "splits" / "dev.csv", args.task, tokenizer, label_map, config["max_length"], service=args.service, parent=args.parent)
    model = AutoModelForSequenceClassification.from_pretrained(
        config["model_name"], num_labels=len(label_map), id2label={v: k for k, v in label_map.items()}, label2id=label_map
    )
    output_dir = ROOT / config["output_path"].format(task=args.task)
    if args.service:
        output_dir = output_dir / args.service
    if args.parent:
        output_dir = output_dir / args.parent
    use_parent_mask = args.task == "intent" and args.parent is None
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
        remove_unused_columns=not use_parent_mask,
    )
    trainer_class = Trainer
    trainer_kwargs = {}

    use_class_weights = config.get("class_weighting") == "balanced"

    if use_parent_mask or use_class_weights:
        import torch

        class_weights = None

        if use_class_weights:
            counts = np.bincount(
                [label_map[label] for label in train.labels],
                minlength=len(label_map),
            )
            class_weights = len(train) / (
                len(label_map) * np.maximum(counts, 1)
            )

        class StructuredTrainer(Trainer):
            def compute_loss(
                self,
                model,
                inputs,
                return_outputs=False,
                **kwargs,
            ):
                labels = inputs.pop("labels")
                label_mask = inputs.pop("label_mask", None)

                outputs = model(**inputs)
                logits = outputs.logits

                if use_parent_mask:
                    if label_mask is None:
                        raise ValueError(
                            "Service-level intent training requires label_mask"
                        )

                    label_mask = label_mask.to(
                        device=logits.device,
                        dtype=torch.bool,
                    )

                    if label_mask.shape != logits.shape:
                        raise ValueError(
                            "Intent label mask shape does not match logits: "
                            f"{tuple(label_mask.shape)} vs {tuple(logits.shape)}"
                        )

                    true_label_allowed = label_mask.gather(
                        1,
                        labels.unsqueeze(1),
                    )

                    if not bool(true_label_allowed.all().item()):
                        raise ValueError(
                            "Gold intent is outside its parent's allowed label set"
                        )

                    logits = logits.masked_fill(
                        ~label_mask,
                        torch.finfo(logits.dtype).min,
                    )

                    # Trainer uses returned logits for DEV prediction/metrics,
                    # so evaluation follows the same parent constraint as training.
                    outputs.logits = logits

                weight_tensor = None

                if class_weights is not None:
                    weight_tensor = torch.tensor(
                        class_weights,
                        device=logits.device,
                        dtype=logits.dtype,
                    )

                loss = torch.nn.functional.cross_entropy(
                    logits,
                    labels,
                    weight=weight_tensor,
                )

                return (loss, outputs) if return_outputs else loss

        trainer_class = StructuredTrainer

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
