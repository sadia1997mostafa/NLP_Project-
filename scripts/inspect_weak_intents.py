from pathlib import Path

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support


SERVICES = ["TAX", "DRIVING_LICENCE"]

ROOTS = {
    "OLD": Path("models/evaluation/intent_pre_nlu_aug_20260919"),
    "NEW": Path("models/evaluation/intent"),
}


for service in SERVICES:
    print()
    print("=" * 90)
    print(service)
    print("=" * 90)

    for version, root in ROOTS.items():
        path = root / f"{service}_dev_predictions.csv"

        df = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
        )

        labels = sorted(
            set(df["gold_label"])
            | set(df["predicted_label"])
        )

        precision, recall, f1, support = (
            precision_recall_fscore_support(
                df["gold_label"],
                df["predicted_label"],
                labels=labels,
                zero_division=0,
            )
        )

        per_intent = pd.DataFrame(
            {
                "intent": labels,
                "support": support,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        ).sort_values(
            ["f1", "intent"]
        )

        wrong = (
            df[
                df["gold_label"]
                != df["predicted_label"]
            ]
            .groupby(
                ["gold_label", "predicted_label"]
            )
            .size()
            .reset_index(name="count")
            .sort_values(
                ["count", "gold_label"],
                ascending=[False, True],
            )
        )

        print()
        print(
            f"--- {version}: "
            "WORST 12 INTENTS ---"
        )
        print(
            per_intent.head(12).to_string(
                index=False
            )
        )

        print()
        print(
            f"--- {version}: "
            "TOP 15 CONFUSIONS ---"
        )
        print(
            wrong.head(15).to_string(
                index=False
            )
        )