"""Create the frozen parent-conditioned intent support inventory."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.models.hierarchy import hierarchy_index


ROOT = Path(__file__).resolve().parents[2]


def build() -> list[dict]:
    train = pd.read_csv(ROOT / "data/splits/train.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    dev = pd.read_csv(ROOT / "data/splits/dev.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    _, parent_to_intents, parent_to_service = hierarchy_index()
    rows = []
    for parent, intents in parent_to_intents.items():
        train_counts = train[train.parent_topic_id.eq(parent)].groupby("query_topic_id").size()
        dev_counts = dev[dev.parent_topic_id.eq(parent)].groupby("query_topic_id").size()
        if set(train_counts.index) != set(intents) or set(dev_counts.index) != set(intents):
            raise ValueError(f"Split label coverage disagrees with frozen taxonomy for {parent}")
        rows.append({
            "service": parent_to_service[parent],
            "parent_topic_id": parent,
            "intent_leaves": len(intents),
            "train_rows": int(train_counts.sum()),
            "dev_rows": int(dev_counts.sum()),
            "classifier_required": len(intents) > 1,
            "train_class_min": int(train_counts.min()),
            "train_class_max": int(train_counts.max()),
            "dev_class_min": int(dev_counts.min()),
            "dev_class_max": int(dev_counts.max()),
            "deterministic_intent": intents[0] if len(intents) == 1 else None,
        })
    output_dir = ROOT / "models/evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_dir / "intent_parent_inventory.csv", index=False, encoding="utf-8", lineterminator="\n")
    summary = {
        "parents": len(rows),
        "single_leaf_deterministic": sum(not row["classifier_required"] for row in rows),
        "multi_leaf_classifiers": sum(row["classifier_required"] for row in rows),
        "inventory": rows,
    }
    (output_dir / "intent_parent_inventory.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return rows


if __name__ == "__main__":
    rows = build()
    print("PARENTS:", len(rows))
    print("DETERMINISTIC SINGLE-LEAF:", sum(not row["classifier_required"] for row in rows))
    print("CLASSIFIERS REQUIRED:", sum(row["classifier_required"] for row in rows))
    for row in rows:
        print(row)
