"""Frozen-contract helpers for service-conditioned parent/intent routing."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "contracts" / "labels.yaml"
LABEL_MAP_DIR = ROOT / "contracts" / "label_maps"


def load_contract() -> dict:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("status") != "frozen":
        raise ValueError("Hierarchical routing requires a frozen label contract")
    return contract


def global_label_map(task: str) -> dict[str, int]:
    path = LABEL_MAP_DIR / f"{task}_labels.json"
    return json.loads(path.read_text(encoding="utf-8"))["label_to_id"]


def hierarchy_index() -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, str]]:
    services_to_parents: dict[str, list[str]] = {}
    parents_to_intents: dict[str, list[str]] = {}
    parent_to_service: dict[str, str] = {}
    for service_id, service in load_contract()["services"].items():
        parents = list(service["parent_topics"])
        services_to_parents[service_id] = parents
        for parent_id, parent in service["parent_topics"].items():
            parent_to_service[parent_id] = service_id
            parents_to_intents[parent_id] = list(parent["query_topics"])
    return services_to_parents, parents_to_intents, parent_to_service


def conditioned_label_map(
    task: str,
    service: str | None = None,
    parent: str | None = None,
) -> dict[str, int]:
    """Return a deterministic local map preserving global-contract order."""
    global_map = global_label_map(task)
    services_to_parents, parents_to_intents, parent_to_service = hierarchy_index()
    if task == "parent":
        if not service or parent:
            raise ValueError("Parent classification requires --service and no --parent")
        labels = services_to_parents.get(service)
        if labels is None:
            raise ValueError(f"Unknown service {service!r}")
    elif task == "intent":
        if not service:
            raise ValueError("Intent classification requires --service")
        if service not in services_to_parents:
            raise ValueError(f"Unknown service {service!r}")
        if parent:
            if parent_to_service.get(parent) != service:
                raise ValueError(f"Parent {parent!r} does not belong to service {service!r}")
            labels = parents_to_intents[parent]
        else:
            labels = [
                intent
                for parent_id in services_to_parents[service]
                for intent in parents_to_intents[parent_id]
            ]
    elif task in {"service", "priority"}:
        if service or parent:
            raise ValueError(f"{task} classification does not accept service/parent scope")
        return global_map
    else:
        raise ValueError(f"Unknown task {task!r}")
    ordered = sorted(labels, key=lambda label: global_map[label])
    return {label: index for index, label in enumerate(ordered)}


def only_intent(service: str, parent: str) -> str | None:
    mapping = conditioned_label_map("intent", service, parent)
    return next(iter(mapping)) if len(mapping) == 1 else None


def contextualize_intent_text(text: str, service: str, parent: str) -> str:
    """Supply upstream routing context without changing the stored query text."""
    return f"[SERVICE={service}] [PARENT={parent}] {text}"
