"""Select, compact, verify, and optionally clean a DEV-selected checkpoint."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def best_checkpoint(run_dir: Path) -> tuple[Path, float, float | None, float | None]:
    states = sorted(
        run_dir.glob("checkpoint-*/trainer_state.json"),
        key=lambda path: int(path.parent.name.split("-")[-1]),
    )
    if not states:
        raise FileNotFoundError(f"No trainer_state.json found under {run_dir}")
    state = json.loads(states[-1].read_text(encoding="utf-8"))
    source = Path(state["best_model_checkpoint"])
    if not source.is_absolute():
        source = (ROOT / source).resolve()
    best_metric = float(state["best_metric"])
    best_log = max(
        (entry for entry in state["log_history"] if "eval_macro_f1" in entry),
        key=lambda entry: entry["eval_macro_f1"],
    )
    if abs(float(best_log["eval_macro_f1"]) - best_metric) > 1e-9:
        raise ValueError("trainer_state best metric disagrees with DEV macro F1 history")
    return source, best_metric, best_log.get("eval_accuracy"), best_log.get("epoch")


def compact_and_verify(
    source: Path,
    target: Path,
    task: str,
    service: str | None,
    parent: str | None,
    dev_macro_f1: float,
    dev_accuracy: float | None,
    best_epoch: float | None,
    expected_labels: int,
) -> dict:
    from transformers import AutoModelForSequenceClassification

    source = source.resolve()
    target = target.resolve()
    if ROOT.resolve() not in target.parents:
        raise ValueError("Final model target must remain inside the repository")
    target.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "model.safetensors"):
        shutil.copy2(source / name, target / name)
    selection = {
        "task": task,
        "service": service,
        "parent_topic_id": parent,
        "source_checkpoint": str(source.relative_to(ROOT)),
        "selection_metric": "dev_macro_f1",
        "dev_macro_f1": dev_macro_f1,
        "dev_accuracy": dev_accuracy,
        "best_epoch": best_epoch,
    }
    (target / "selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    model = AutoModelForSequenceClassification.from_pretrained(target, local_files_only=True)
    if model.config.num_labels != expected_labels:
        raise ValueError(f"Final model has {model.config.num_labels} labels; expected {expected_labels}")
    return selection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--service")
    parser.add_argument("--parent")
    parser.add_argument("--expected-labels", type=int, required=True)
    args = parser.parse_args()
    source, metric, accuracy, epoch = best_checkpoint(args.run_dir.resolve())
    selection = compact_and_verify(source, args.target, args.task, args.service, args.parent, metric, accuracy, epoch, args.expected_labels)
    print(json.dumps(selection, indent=2))
    print("FINAL MODEL VERIFIED:", args.target)


if __name__ == "__main__":
    main()
