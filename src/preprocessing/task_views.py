"""Create model-task views without duplicating the canonical datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .text_normalization import normalize_text
from src.models.hierarchy import contextualize_intent_text


TASK_TARGETS = {
    "service": "service",
    "parent": "parent_topic_id",
    "intent": "query_topic_id",
    "priority": "priority",
}


def project_task(
    frame: pd.DataFrame,
    task: str,
    service: str | None = None,
    parent: str | None = None,
    include_routing_context: bool = False,
) -> pd.DataFrame:
    """Return stable row/family/text/label columns for one classification task."""
    if service is not None:
        if "service" not in frame.columns:
            raise ValueError("Dataset is missing service column")
        frame = frame[frame["service"] == service].copy()
        if frame.empty:
            raise ValueError(f"No rows found for service {service!r}")
    if parent is not None:
        if service is None:
            raise ValueError("A parent filter requires a service filter")
        if "parent_topic_id" not in frame.columns:
            raise ValueError("Dataset is missing parent_topic_id column")
        frame = frame[frame["parent_topic_id"] == parent].copy()
        if frame.empty:
            raise ValueError(f"No rows found for parent {parent!r} in service {service!r}")
    if task not in TASK_TARGETS:
        raise ValueError(f"Unknown task {task!r}; choose from {sorted(TASK_TARGETS)}")
    target = TASK_TARGETS[task]
    required = {"id", "text", "parent_query_id", target}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    context = frame[["service", "parent_topic_id"]].copy() if task == "intent" else None
    result = frame[["id", "parent_query_id", "text", target]].copy()
    result["text"] = result["text"].map(normalize_text)
    if task == "intent":
        result["text"] = [
            contextualize_intent_text(text, row.service, row.parent_topic_id)
            for text, row in zip(result["text"], context.itertuples(index=False))
        ]

        if include_routing_context:
            result["parent_topic_id"] = context["parent_topic_id"].to_numpy()
    return result.rename(columns={target: "label"})


def load_task_view(
    path: str | Path,
    task: str,
    service: str | None = None,
    parent: str | None = None,
    include_routing_context: bool = False,
) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return project_task(
        frame,
        task,
        service=service,
        parent=parent,
        include_routing_context=include_routing_context,
    )
