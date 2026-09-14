"""Derive an auditable error-propagation summary from DEV predictions."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS = ROOT / "models/evaluation/hierarchical_dev_predictions.csv"
METRICS = ROOT / "models/evaluation/hierarchical_dev_metrics.json"
OUTPUT = ROOT / "models/evaluation/hierarchical_dev_error_summary.json"


def boolean_column(frame: pd.DataFrame, name: str) -> pd.Series:
    values = frame[name].astype(str).str.strip().str.lower()
    if not values.isin({"true", "false"}).all():
        raise ValueError(f"{name} contains non-boolean values")
    return values.eq("true")


def main() -> None:
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    if metrics.get("evaluation_scope") != "DEV only":
        raise ValueError("Hierarchy metrics are not marked DEV only")
    if metrics.get("test_data_used") is not False:
        raise ValueError("Hierarchy metrics do not explicitly exclude TEST")

    frame = pd.read_csv(PREDICTIONS, dtype=str, keep_default_na=False)
    service_error = boolean_column(frame, "service_routing_error")
    parent_oracle_error = boolean_column(frame, "parent_error_after_oracle_service")
    parent_predicted_error = boolean_column(frame, "parent_error_predicted_route")
    intent_oracle_error = boolean_column(frame, "intent_error_after_oracle_route")
    intent_predicted_error = boolean_column(frame, "intent_error_predicted_route")
    priority_error = boolean_column(frame, "priority_error")
    ood_rejection = boolean_column(frame, "is_ood")

    correct_service = ~service_error
    correct_predicted_parent = ~parent_predicted_error
    correct_predicted_intent = ~intent_predicted_error
    correct_priority = ~priority_error
    accepted = ~ood_rejection

    payload = {
        "evaluation_scope": "DEV only",
        "test_data_used": False,
        "rows": len(frame),
        "error_propagation": {
            "service_routing_errors": int(service_error.sum()),
            "parent_errors_with_oracle_service": int(parent_oracle_error.sum()),
            "parent_errors_after_correct_predicted_service": int(
                (correct_service & parent_predicted_error).sum()
            ),
            "intent_errors_with_oracle_service_and_parent": int(
                intent_oracle_error.sum()
            ),
            "intent_errors_after_correct_predicted_service_and_parent": int(
                (
                    correct_service
                    & correct_predicted_parent
                    & intent_predicted_error
                ).sum()
            ),
            "priority_errors": int(priority_error.sum()),
            "ood_false_rejections_on_in_domain_dev": int(ood_rejection.sum()),
        },
        "conditional_counts": {
            "correct_service": int(correct_service.sum()),
            "correct_service_and_parent": int(
                (correct_service & correct_predicted_parent).sum()
            ),
            "correct_service_parent_and_intent": int(
                (
                    correct_service
                    & correct_predicted_parent
                    & correct_predicted_intent
                ).sum()
            ),
            "correct_service_parent_intent_and_priority": int(
                (
                    correct_service
                    & correct_predicted_parent
                    & correct_predicted_intent
                    & correct_priority
                ).sum()
            ),
            "full_match_including_in_domain_ood_acceptance": int(
                (
                    correct_service
                    & correct_predicted_parent
                    & correct_predicted_intent
                    & correct_priority
                    & accepted
                ).sum()
            ),
        },
        "full_match_including_in_domain_ood_acceptance_accuracy": float(
            (
                correct_service
                & correct_predicted_parent
                & correct_predicted_intent
                & correct_priority
                & accepted
            ).mean()
        ),
        "source_artifacts": {
            "metrics": METRICS.relative_to(ROOT).as_posix(),
            "predictions": PREDICTIONS.relative_to(ROOT).as_posix(),
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
