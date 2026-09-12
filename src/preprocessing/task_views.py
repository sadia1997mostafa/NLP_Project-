"""Create model-task views without duplicating the canonical datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .text_normalization import normalize_text


TASK_TARGETS = {
    "service": "service",
    "parent": "parent_topic_id",
    "intent": "query_topic_id",
    "priority": "priority",
}


def project_task(frame: pd.DataFrame, task: str, service: str | None = None) -> pd.DataFrame:
    """Return stable row/family/text/label columns for one classification task."""
    if service is not None:
        if "service" not in frame.columns:
            raise ValueError("Dataset is missing service column")
        frame = frame[frame["service"] == service].copy()
        if frame.empty:
            raise ValueError(f"No rows found for service {service!r}")
    if task not in TASK_TARGETS:
        raise ValueError(f"Unknown task {task!r}; choose from {sorted(TASK_TARGETS)}")
    target = TASK_TARGETS[task]
    required = {"id", "text", "parent_query_id", target}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    result = frame[["id", "parent_query_id", "text", target]].copy()
    result["text"] = result["text"].map(normalize_text)
    return result.rename(columns={target: "label"})


def load_task_view(path: str | Path, task: str, service: str | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return project_task(frame, task, service=service)
