"""Run the two predefined DEV-only priority experiments and select by macro F1."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

from src.models.checkpoint_selection import best_checkpoint, compact_and_verify
from src.models.evaluate_checkpoint import evaluate
from src.models.hierarchy import conditioned_label_map


ROOT = Path(__file__).resolve().parents[2]
EVALUATION = ROOT / "models/evaluation"
EXPERIMENTS = {
    "unweighted": ROOT / "configs/classifier_priority_unweighted.yaml",
    "balanced": ROOT / "configs/classifier_priority_balanced.yaml",
}


def _remove_exact(path: Path, required_parent: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != required_parent.resolve():
        raise ValueError(f"Refusing to remove unexpected path: {resolved}")
    if resolved.exists():
        for attempt in range(5):
            try:
                shutil.rmtree(resolved)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(1)


def main() -> None:
    train = pd.read_csv(
        ROOT / "data/splits/train.csv",
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    dev = pd.read_csv(
        ROOT / "data/splits/dev.csv",
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    distributions = {
        "train": dict(sorted(Counter(train.priority).items())),
        "dev": dict(sorted(Counter(dev.priority).items())),
        "train_by_service": {
            service: dict(sorted(Counter(group.priority).items()))
            for service, group in train.groupby("service")
        },
    }
    print(json.dumps(distributions, indent=2))

    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    labels = conditioned_label_map("priority")
    results = []
    candidate_root = ROOT / "models/final/priority_candidates"
    checkpoint_root = ROOT / "models/checkpoints"
    for name, config in EXPERIMENTS.items():
        print(f"TRAIN PRIORITY {name.upper()}", flush=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "src.models.train_classifier",
                "--task",
                "priority",
                "--config",
                str(config),
                "--execute-training",
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        run_dir = ROOT / "models/checkpoints" / f"priority_{name}"
        source, macro_f1, accuracy, epoch = best_checkpoint(run_dir)
        candidate = candidate_root / name
        selection = compact_and_verify(
            source,
            candidate,
            "priority",
            None,
            None,
            macro_f1,
            accuracy,
            epoch,
            len(labels),
        )
        metrics = evaluate(
            candidate,
            "priority",
            EVALUATION / f"priority_{name}_dev_predictions.csv",
            EVALUATION / f"priority_{name}_dev_metrics.json",
        )
        _remove_exact(run_dir, checkpoint_root)
        results.append(
            {
                "experiment": name,
                "selection": selection,
                "metrics": metrics,
                "candidate": candidate,
            }
        )

    selected = max(
        results,
        key=lambda row: (row["metrics"]["macro_f1"], row["metrics"]["accuracy"]),
    )
    final = ROOT / "models/final/priority"
    if final.exists():
        _remove_exact(final, ROOT / "models/final")
    final.mkdir(parents=True)
    for filename in ("config.json", "model.safetensors"):
        shutil.copy2(selected["candidate"] / filename, final / filename)
    final_selection = {
        **selected["selection"],
        "experiment": selected["experiment"],
        "selection_metric": "dev_macro_f1",
        "dev_macro_f1": selected["metrics"]["macro_f1"],
        "dev_accuracy": selected["metrics"]["accuracy"],
        "comparison": {
            row["experiment"]: {
                "dev_accuracy": row["metrics"]["accuracy"],
                "dev_macro_f1": row["metrics"]["macro_f1"],
            }
            for row in results
        },
    }
    (final / "selection.json").write_text(
        json.dumps(final_selection, indent=2) + "\n",
        encoding="utf-8",
    )
    from transformers import AutoModelForSequenceClassification

    model = AutoModelForSequenceClassification.from_pretrained(final, local_files_only=True)
    if model.config.num_labels != 3:
        raise ValueError("Selected priority model does not have 3 labels")

    summary = {
        "selection_basis": "DEV macro F1 only",
        "test_data_used": False,
        "class_distribution": distributions,
        "experiments": [
            {
                "experiment": row["experiment"],
                "dev_accuracy": row["metrics"]["accuracy"],
                "dev_macro_f1": row["metrics"]["macro_f1"],
                "confusion_matrix": row["metrics"]["confusion_matrix"],
                "label_order": row["metrics"]["label_order"],
            }
            for row in results
        ],
        "selected": selected["experiment"],
        "final_model": str(final.relative_to(ROOT)),
    }
    (EVALUATION / "priority_training_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    for candidate in candidate_root.iterdir():
        _remove_exact(candidate, candidate_root)
    candidate_root.rmdir()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
