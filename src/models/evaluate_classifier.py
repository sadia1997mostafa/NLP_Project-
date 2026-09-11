"""Evaluate saved gold/prediction CSVs without inventing model results."""

from __future__ import annotations

import argparse
import json

import pandas as pd

from src.models.metrics import classification_metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", help="CSV containing gold_label,predicted_label")
    parser.add_argument("--output", help="Optional JSON metrics output")
    args = parser.parse_args()
    frame = pd.read_csv(args.predictions, dtype=str, keep_default_na=False)
    needed = {"gold_label", "predicted_label"}
    if not needed.issubset(frame):
        raise ValueError(f"Prediction CSV must contain {sorted(needed)}")
    labels = sorted(set(frame["gold_label"]) | set(frame["predicted_label"]))
    result = classification_metrics(frame["gold_label"], frame["predicted_label"], labels)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
