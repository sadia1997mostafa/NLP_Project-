"""Train six service-level intent models with parent context and routed logits."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

from src.models.build_intent_inventory import build as build_inventory
from src.models.checkpoint_selection import best_checkpoint, compact_and_verify
from src.models.evaluate_checkpoint import evaluate
from src.models.hierarchy import conditioned_label_map


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/classifier_intent_small_balanced.yaml"
EVALUATION = ROOT / "models/evaluation"


def safe_remove(path: Path) -> None:
    """Remove one verified service checkpoint directory, retrying Windows locks."""
    resolved = path.resolve()
    checkpoint_root = (ROOT / "models/checkpoints/intent").resolve()
    if resolved.parent != checkpoint_root:
        raise ValueError(f"Refusing to clean unexpected path: {resolved}")
    for attempt in range(5):
        try:
            shutil.rmtree(resolved)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(1)


def completed_result(
    service: str,
    labels: dict[str, int],
    final_dir: Path,
    metrics_path: Path,
) -> dict | None:
    """Return a load-verified result so interrupted runs can safely resume."""
    selection_path = final_dir / "selection.json"
    if not selection_path.exists() or not metrics_path.exists():
        return None
    from transformers import AutoModelForSequenceClassification

    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    model = AutoModelForSequenceClassification.from_pretrained(
        final_dir,
        local_files_only=True,
    )
    if model.config.num_labels != len(labels):
        raise ValueError(
            f"Completed {service} model has {model.config.num_labels} labels; "
            f"expected {len(labels)}"
        )
    return {
        "service": service,
        "intent_leaves": len(labels),
        "status": "selected",
        "selected_checkpoint": selection["source_checkpoint"],
        "best_epoch": selection["best_epoch"],
        "selection_dev_accuracy_unmasked": selection["dev_accuracy"],
        "selection_dev_macro_f1_unmasked": selection["dev_macro_f1"],
        "oracle_parent_routed_dev_accuracy": metrics["accuracy"],
        "oracle_parent_routed_dev_macro_f1": metrics["macro_f1"],
        "final_model": str(final_dir.relative_to(ROOT)),
    }


def run(execute_training: bool = False, train_file: Path | None = None) -> list[dict]:
    train_file = train_file or (ROOT / "data/splits/train.csv")
    if not train_file.is_absolute():
        train_file = ROOT / train_file
    inventory = build_inventory()
    print(
        "Intent hierarchy: 5 deterministic routes; 6 service-level "
        "conditioned models cover 44 multi-leaf parents"
    )
    if not execute_training:
        for service in sorted({row["service"] for row in inventory}):
            mapping = conditioned_label_map("intent", service)
            print(service, len(mapping), "service intent labels")
        print("DRY RUN ONLY: no model loaded or trained.")
        return inventory

    results: list[dict] = []
    failures: list[dict] = []
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    services = sorted({row["service"] for row in inventory})
    for number, service in enumerate(services, start=1):
        labels = conditioned_label_map("intent", service)
        run_dir = ROOT / "models/checkpoints/intent" / service
        final_dir = ROOT / "models/final/intent" / service
        prediction_path = EVALUATION / "intent" / f"{service}_dev_predictions.csv"
        metrics_path = EVALUATION / "intent" / f"{service}_dev_metrics.json"
        try:
            completed = completed_result(service, labels, final_dir, metrics_path)
            if completed is not None:
                print(f"[{number}/{len(services)}] REUSE VERIFIED {service}", flush=True)
                if run_dir.exists():
                    safe_remove(run_dir)
                results.append(completed)
                continue

            print(
                f"[{number}/{len(services)}] TRAIN {service} ({len(labels)} labels)",
                flush=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.models.train_classifier",
                    "--task",
                    "intent",
                    "--service",
                    service,
                    "--config",
                    str(CONFIG),
                    "--train-file",
                    str(train_file),
                    "--execute-training",
                ],
                cwd=ROOT,
                env=env,
                check=True,
            )
            source, metric, accuracy, epoch = best_checkpoint(run_dir)
            selection = compact_and_verify(
                source,
                final_dir,
                "intent",
                service,
                None,
                metric,
                accuracy,
                epoch,
                len(labels),
            )
            metrics = evaluate(
                final_dir,
                "intent",
                prediction_path,
                metrics_path,
                service,
            )
            safe_remove(run_dir)
            results.append(
                {
                    "service": service,
                    "intent_leaves": len(labels),
                    "status": "selected",
                    "selected_checkpoint": selection["source_checkpoint"],
                    "best_epoch": epoch,
                    "selection_dev_accuracy_unmasked": accuracy,
                    "selection_dev_macro_f1_unmasked": metric,
                    "oracle_parent_routed_dev_accuracy": metrics["accuracy"],
                    "oracle_parent_routed_dev_macro_f1": metrics["macro_f1"],
                    "final_model": str(final_dir.relative_to(ROOT)),
                }
            )
        except Exception as exc:
            failure = {"service": service, "status": "failed", "error": repr(exc)}
            failures.append(failure)
            results.append(failure)
            print("FAILED:", service, repr(exc), flush=True)
            traceback.print_exc()

    parent_results = []
    service_results = {row["service"]: row for row in results}
    for row in inventory:
        if not row["classifier_required"]:
            parent_results.append(
                {
                    **row,
                    "status": "deterministic_single_leaf",
                    "dev_accuracy": 1.0,
                    "dev_macro_f1": 1.0,
                }
            )
            continue
        service_result = service_results.get(row["service"], {})
        if service_result.get("status") != "selected":
            parent_results.append({**row, "status": "failed_service_model"})
            continue
        predictions = pd.read_csv(
            EVALUATION / "intent" / f"{row['service']}_dev_predictions.csv",
            dtype=str,
            keep_default_na=False,
        )
        subset = predictions[predictions.parent_topic_id.eq(row["parent_topic_id"])]
        from src.models.metrics import classification_metrics

        labels = list(
            conditioned_label_map("intent", row["service"], row["parent_topic_id"])
        )
        metric_row = classification_metrics(
            subset.gold_label,
            subset.predicted_label,
            labels,
        )
        parent_results.append(
            {
                **row,
                "status": "routed_service_model",
                "dev_accuracy": metric_row["accuracy"],
                "dev_macro_f1": metric_row["macro_f1"],
            }
        )

    EVALUATION.mkdir(parents=True, exist_ok=True)
    payload = {
        "selection_basis": "DEV macro F1 only",
        "test_data_used": False,
        "parents": len(parent_results),
        "architecture": (
            "six service-level XLM-R intent models with service/parent context; "
            "logits masked to routed parent"
        ),
        "deterministic_routes": sum(
            x["status"] == "deterministic_single_leaf" for x in parent_results
        ),
        "selected_classifiers": sum(x["status"] == "selected" for x in results),
        "failed_classifiers": len(failures),
        "service_models": results,
        "parent_results": parent_results,
    }
    EVALUATION.mkdir(parents=True, exist_ok=True)
    (EVALUATION / "intent_training_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame(parent_results).to_csv(
        EVALUATION / "intent_training_summary.csv",
        index=False,
        encoding="utf-8",
        lineterminator="\n",
    )
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "parents",
                    "deterministic_routes",
                    "selected_classifiers",
                    "failed_classifiers",
                )
            },
            indent=2,
        )
    )
    if failures:
        raise SystemExit(1)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-training", action="store_true")
    parser.add_argument("--train-file", type=Path, default=ROOT / "data/splits/train.csv")
    args = parser.parse_args()
    run(args.execute_training, args.train_file)
