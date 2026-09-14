"""Lazy, dependency-light dataset loading for Transformer classifiers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.models.hierarchy import conditioned_label_map
from src.preprocessing.task_views import load_task_view


class EncodedTextDataset:
    """Torch-compatible dataset; torch is required only when training starts."""

    def __init__(
        self,
        texts,
        labels,
        tokenizer,
        label_to_id,
        max_length: int = 128,
        label_masks=None,
    ):
        self.texts = list(texts)
        self.labels = list(labels)
        self.tokenizer = tokenizer
        self.label_to_id = dict(label_to_id)
        self.max_length = max_length

        self.label_masks = None if label_masks is None else list(label_masks)

        if self.label_masks is not None and len(self.label_masks) != len(self.texts):
            raise ValueError("label_masks must have one mask per example")

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

        if self.label_masks is not None:
            encoded["label_mask"] = self.label_masks[index]

        return encoded


def load_dataset(
    path: str | Path,
    task: str,
    tokenizer,
    label_to_id,
    max_length=128,
    service: str | None = None,
    parent: str | None = None,
):
    include_routing_context = task == "intent" and parent is None

    view = load_task_view(
        path,
        task,
        service=service,
        parent=parent,
        include_routing_context=include_routing_context,
    )

    label_masks = None

    if include_routing_context:
        if not service:
            raise ValueError("Service-level intent training requires a service")
        if "parent_topic_id" not in view.columns:
            raise ValueError("Intent task view is missing parent_topic_id")

        label_masks = []

        for parent_id in view["parent_topic_id"]:
            valid_labels = conditioned_label_map(
                "intent",
                service=service,
                parent=parent_id,
            )

            mask = [False] * len(label_to_id)

            for label in valid_labels:
                if label not in label_to_id:
                    raise ValueError(
                        f"Intent {label!r} for parent {parent_id!r} "
                        "is missing from the service-level label map"
                    )
                mask[label_to_id[label]] = True

            if not any(mask):
                raise ValueError(
                    f"Parent {parent_id!r} produced an empty intent mask"
                )

            label_masks.append(mask)

    return EncodedTextDataset(
        view["text"],
        view["label"],
        tokenizer,
        label_to_id,
        max_length,
        label_masks=label_masks,
    )
