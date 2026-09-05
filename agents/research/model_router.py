from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

SCHEMA_VERSION = "2.0"
METHOD_VERSION = "v2"

SUPPORTED_TASKS = ("research", "drafting", "revision", "editorial")
SUPPORTED_POLICIES = ("fast", "balanced", "quality")
SUPPORTED_PROVIDER_TYPES = ("openai", "anthropic", "other")

DEFAULT_POLICY = {
    "research": "balanced",
    "drafting": "quality",
    "revision": "balanced",
    "editorial": "fast",
}

# Provider/model metadata is deliberately configuration only. Core never
# imports provider SDKs, reads credentials, or makes network calls.
DEFAULT_PROVIDER_REGISTRY: dict[str, dict[str, Any]] = {
    "openai-gpt-5.6": {
        "provider": "openai",
        "provider_type": "openai",
        "model": "gpt-5.6",
        "adapter": "openai",
        "capabilities": ["quality", "balanced"],
        "available": True,
        "priority": 10,
    },
    "anthropic-claude-sonnet": {
        "provider": "anthropic",
        "provider_type": "anthropic",
        "model": "claude-sonnet",
        "adapter": "anthropic",
        "capabilities": ["quality", "balanced"],
        "available": True,
        "priority": 20,
    },
    "other-fast": {
        "provider": "other-provider",
        "provider_type": "other",
        "model": "other-fast",
        "adapter": "other-provider",
        "capabilities": ["fast"],
        "available": True,
        "priority": 30,
    },
}

POLICY_FALLBACKS = {
    "quality": ("quality", "balanced", "fast"),
    "balanced": ("balanced", "quality", "fast"),
    "fast": ("fast", "balanced", "quality"),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _router_id(task: str, policy: str, effective_policy: str, model: str, provider: str) -> str:
    payload = {
        "task": task,
        "policy": policy,
        "effective_policy": effective_policy,
        "model": model,
        "provider": provider,
        "schema_version": SCHEMA_VERSION,
        "method_version": METHOD_VERSION,
    }
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:16]
    return f"model_route_{digest}"


def _validate_registry(registry: dict[str, dict[str, Any]]) -> None:
    if not isinstance(registry, dict) or not registry:
        raise ValueError("Provider registry must be a non-empty mapping")

    for key, spec in registry.items():
        if not isinstance(key, str) or not key:
            raise ValueError("Provider registry keys must be non-empty strings")
        if not isinstance(spec, dict):
            raise ValueError(f"Provider registry entry must be an object: {key}")
        provider = spec.get("provider")
        provider_type = spec.get("provider_type")
        model = spec.get("model")
        adapter = spec.get("adapter")
        capabilities = spec.get("capabilities")
        available = spec.get("available")
        priority = spec.get("priority")
        if not provider or not provider_type or not model or not adapter:
            raise ValueError(f"Provider registry entry is incomplete: {key}")
        if provider_type not in SUPPORTED_PROVIDER_TYPES:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        if not isinstance(capabilities, list) or not capabilities or any(
            capability not in SUPPORTED_POLICIES for capability in capabilities
        ):
            raise ValueError(f"Invalid capabilities: {key}")
        if not isinstance(available, bool):
            raise ValueError(f"Availability must be boolean: {key}")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
            raise ValueError(f"Priority must be a non-negative integer: {key}")


def _candidate_sort_key(spec: dict[str, Any], key: str) -> tuple[int, str, str, str, str]:
    return (
        spec["priority"],
        spec["provider_type"],
        spec["provider"],
        spec["model"],
        key,
    )


def build_model_route(
    task: str,
    *,
    policy: str | None = None,
    registry: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Select a deterministic provider/model from an injected registry.

    The router is a pure Core contract layer: it selects metadata only. The
    selected adapter is responsible for any later external API interaction.
    """
    if task not in SUPPORTED_TASKS:
        raise ValueError(f"Unsupported task: {task}")

    selected_policy = policy or DEFAULT_POLICY[task]
    if selected_policy not in SUPPORTED_POLICIES:
        raise ValueError(f"Unsupported policy: {selected_policy}")

    active_registry = deepcopy(registry if registry is not None else DEFAULT_PROVIDER_REGISTRY)
    _validate_registry(active_registry)

    effective_policy = None
    candidates: list[tuple[str, dict[str, Any]]] = []
    for candidate_policy in POLICY_FALLBACKS[selected_policy]:
        candidates = [
            (key, spec)
            for key, spec in active_registry.items()
            if spec["available"] is True and candidate_policy in spec["capabilities"]
        ]
        if candidates:
            effective_policy = candidate_policy
            break

    if not candidates or effective_policy is None:
        raise ValueError(f"No available provider/model for policy: {selected_policy}")

    key, selected = sorted(candidates, key=lambda item: _candidate_sort_key(item[1], item[0]))[0]

    return {
        "route_id": _router_id(
            task,
            selected_policy,
            effective_policy,
            selected["model"],
            selected["provider"],
        ),
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "model_route_ready",
        "task": task,
        "policy": selected_policy,
        "effective_policy": effective_policy,
        "provider": selected["provider"],
        "provider_type": selected["provider_type"],
        "model": selected["model"],
        "adapter": selected["adapter"],
        "capabilities": sorted(set(selected["capabilities"])),
        "selection": {
            "fallback_used": effective_policy != selected_policy,
            "priority": selected["priority"],
            "registry_key": key,
        },
        "audit": {
            "method": "deterministic_provider_registry_policy",
            "version": METHOD_VERSION,
            "network_access": False,
            "provider_call": False,
            "credential_access": False,
            "validation_status": "validated",
        },
    }
