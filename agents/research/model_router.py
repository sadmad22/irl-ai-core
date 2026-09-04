from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

SUPPORTED_TASKS = ("research", "drafting", "revision", "editorial")
DEFAULT_POLICY = {
    "research": "balanced",
    "drafting": "quality",
    "revision": "balanced",
    "editorial": "fast",
}

MODEL_CATALOG = {
    "mock-balanced": {"provider": "mock", "capability": "balanced", "available": True},
    "mock-quality": {"provider": "mock", "capability": "quality", "available": True},
    "mock-fast": {"provider": "mock", "capability": "fast", "available": True},
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _router_id(task: str, policy: str, model: str) -> str:
    payload = {"task": task, "policy": policy, "model": model, "schema_version": SCHEMA_VERSION, "method_version": METHOD_VERSION}
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:16]
    return f"model_route_{digest}"


def build_model_route(
    task: str,
    *,
    policy: str | None = None,
    catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Select a deterministic model from an injected catalog without network access."""
    if task not in SUPPORTED_TASKS:
        raise ValueError(f"Unsupported task: {task}")

    selected_policy = policy or DEFAULT_POLICY[task]
    active_catalog = deepcopy(catalog if catalog is not None else MODEL_CATALOG)
    candidates = [
        name for name, spec in active_catalog.items()
        if spec.get("available") is True and spec.get("capability") == selected_policy
    ]
    if not candidates:
        raise ValueError(f"No available model for policy: {selected_policy}")

    model = sorted(candidates)[0]
    provider = active_catalog[model].get("provider")
    if not provider:
        raise ValueError(f"Model provider is missing: {model}")

    return {
        "route_id": _router_id(task, selected_policy, model),
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "model_route_ready",
        "task": task,
        "policy": selected_policy,
        "model": model,
        "provider": provider,
        "audit": {
            "method": "deterministic_capability_policy",
            "version": METHOD_VERSION,
            "network_access": False,
            "validation_status": "validated",
        },
    }
