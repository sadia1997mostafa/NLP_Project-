"""Lazy, dependency-light dataset loading for Transformer classifiers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.preprocessing.task_views import load_task_view


class EncodedTextDataset:
    """Torch-compatible dataset; torch is required only when training starts."""

    def __init__(self, texts, labels, tokenizer, label_to_id, max_length: int = 128):
        self.texts = list(texts)
        self.labels = list(labels)
        self.tokenizer = tokenizer
        self.label_to_id = dict(label_to_id)
        self.max_length = max_length
        unknown = sorted(set(self.labels) - set(self.label_to_id))
        if unknown:
            raise ValueError(f"Unknown labels in dataset: {unknown}")

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, index: int) -> dict[str, Any]:
        encoded = self.tokenizer(
            self.texts[index],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
        )
        encoded["labels"] = self.label_to_id[self.labels[index]]
        return encoded


def load_dataset(path: str | Path, task: str, tokenizer, label_to_id, max_length=128, service: str | None = None):
    view = load_task_view(path, task, service=service)
    return EncodedTextDataset(
        view["text"], view["label"], tokenizer, label_to_id, max_length
    )
