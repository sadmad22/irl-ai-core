from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.model_router import (
    DEFAULT_PROVIDER_REGISTRY,
    build_model_route,
)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "model-route.schema.json"


def test_route_matches_v2_schema():
    document = build_model_route("drafting")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(document)) == []


def test_default_registry_covers_required_provider_types():
    providers = {spec["provider_type"] for spec in DEFAULT_PROVIDER_REGISTRY.values()}
    assert {"openai", "anthropic", "other"}.issubset(providers)


def test_default_policy_is_task_specific():
    assert build_model_route("research")["policy"] == "balanced"
    assert build_model_route("drafting")["policy"] == "quality"
    assert build_model_route("editorial")["policy"] == "fast"


def test_openai_model_can_be_selected():
    registry = {
        "openai-quality": {
            "provider": "openai",
            "provider_type": "openai",
            "model": "gpt-quality",
            "adapter": "openai",
            "capabilities": ["quality"],
            "available": True,
            "priority": 10,
        }
    }
    route = build_model_route("drafting", registry=registry)
    assert route["provider_type"] == "openai"
    assert route["provider"] == "openai"
    assert route["model"] == "gpt-quality"
    assert route["adapter"] == "openai"


def test_anthropic_model_can_be_selected():
    registry = {
        "anthropic-balanced": {
            "provider": "anthropic",
            "provider_type": "anthropic",
            "model": "claude-balanced",
            "adapter": "anthropic",
            "capabilities": ["balanced"],
            "available": True,
            "priority": 10,
        }
    }
    route = build_model_route("research", registry=registry)
    assert route["provider_type"] == "anthropic"
    assert route["model"] == "claude-balanced"


def test_other_provider_can_be_selected():
    registry = {
        "custom-model": {
            "provider": "custom-provider",
            "provider_type": "other",
            "model": "custom-fast",
            "adapter": "custom-provider",
            "capabilities": ["fast"],
            "available": True,
            "priority": 10,
        }
    }
    route = build_model_route("editorial", registry=registry)
    assert route["provider_type"] == "other"
    assert route["provider"] == "custom-provider"
    assert route["model"] == "custom-fast"


def test_priority_then_stable_metadata_produces_deterministic_selection():
    registry = {
        "z-model": {
            "provider": "provider-z",
            "provider_type": "other",
            "model": "model-z",
            "adapter": "adapter-z",
            "capabilities": ["quality"],
            "available": True,
            "priority": 20,
        },
        "a-model": {
            "provider": "provider-a",
            "provider_type": "openai",
            "model": "model-a",
            "adapter": "openai",
            "capabilities": ["quality"],
            "available": True,
            "priority": 10,
        },
    }
    first = build_model_route("drafting", registry=registry)
    second = build_model_route("drafting", registry=dict(reversed(list(registry.items()))))
    assert first == second
    assert first["model"] == "model-a"


def test_unavailable_models_are_not_selected():
    registry = {
        "unavailable": {
            "provider": "openai",
            "provider_type": "openai",
            "model": "gpt-test",
            "adapter": "openai",
            "capabilities": ["quality"],
            "available": False,
            "priority": 1,
        }
    }
    with pytest.raises(ValueError, match="No available provider/model"):
        build_model_route("drafting", registry=registry)


def test_policy_fallback_is_explicit():
    registry = {
        "fast-only": {
            "provider": "other-provider",
            "provider_type": "other",
            "model": "fast-model",
            "adapter": "other-provider",
            "capabilities": ["fast"],
            "available": True,
            "priority": 1,
        }
    }
    route = build_model_route("drafting", registry=registry)
    assert route["policy"] == "quality"
    assert route["effective_policy"] == "fast"
    assert route["selection"]["fallback_used"] is True


def test_exact_policy_is_preferred_over_fallback_policy():
    registry = {
        "fast": {
            "provider": "other-provider",
            "provider_type": "other",
            "model": "fast-model",
            "adapter": "other-provider",
            "capabilities": ["fast"],
            "available": True,
            "priority": 1,
        },
        "quality": {
            "provider": "openai",
            "provider_type": "openai",
            "model": "quality-model",
            "adapter": "openai",
            "capabilities": ["quality"],
            "available": True,
            "priority": 50,
        },
    }
    route = build_model_route("drafting", registry=registry)
    assert route["effective_policy"] == "quality"
    assert route["selection"]["fallback_used"] is False
    assert route["model"] == "quality-model"


def test_registry_is_not_mutated():
    registry = copy.deepcopy(DEFAULT_PROVIDER_REGISTRY)
    before = copy.deepcopy(registry)
    build_model_route("research", registry=registry)
    assert registry == before


def test_unsupported_task_is_rejected():
    with pytest.raises(ValueError, match="Unsupported task"):
        build_model_route("translation")


def test_unsupported_policy_is_rejected():
    with pytest.raises(ValueError, match="Unsupported policy"):
        build_model_route("research", policy="cheap")


def test_invalid_provider_type_is_rejected():
    registry = copy.deepcopy(DEFAULT_PROVIDER_REGISTRY)
    registry["bad"]["provider_type"] = "unknown"
    with pytest.raises(ValueError, match="Unsupported provider type"):
        build_model_route("research", registry=registry)


def test_incomplete_registry_entry_is_rejected():
    registry = {"broken": {"provider": "openai", "available": True}}
    with pytest.raises(ValueError, match="incomplete"):
        build_model_route("research", registry=registry)


def test_invalid_capabilities_are_rejected():
    registry = copy.deepcopy(DEFAULT_PROVIDER_REGISTRY)
    registry["bad"]["capabilities"] = ["unknown"]
    with pytest.raises(ValueError, match="Invalid capabilities"):
        build_model_route("research", registry=registry)


def test_invalid_priority_is_rejected():
    registry = copy.deepcopy(DEFAULT_PROVIDER_REGISTRY)
    registry["bad"]["priority"] = -1
    with pytest.raises(ValueError, match="Priority"):
        build_model_route("research", registry=registry)


def test_no_candidates_after_all_fallbacks_is_rejected():
    registry = {
        "editorial-only": {
            "provider": "other-provider",
            "provider_type": "other",
            "model": "editorial-model",
            "adapter": "other-provider",
            "capabilities": ["fast"],
            "available": False,
            "priority": 1,
        }
    }
    with pytest.raises(ValueError, match="No available provider/model"):
        build_model_route("research", registry=registry)


def test_route_id_is_deterministic():
    registry = copy.deepcopy(DEFAULT_PROVIDER_REGISTRY)
    assert build_model_route("drafting", registry=registry)["route_id"] == build_model_route(
        "drafting", registry=registry
    )["route_id"]


def test_audit_proves_core_has_no_provider_call_or_credentials():
    audit = build_model_route("research")["audit"]
    assert audit["network_access"] is False
    assert audit["provider_call"] is False
    assert audit["credential_access"] is False


def test_provider_adapter_is_metadata_only():
    route = build_model_route("research")
    assert isinstance(route["adapter"], str)
    assert route["audit"]["provider_call"] is False


def test_route_schema_rejects_unexpected_property():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    document = build_model_route("research")
    document["unexpected"] = True
    errors = list(Draft202012Validator(schema).iter_errors(document))
    assert errors
