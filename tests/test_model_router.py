from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.model_router import build_model_route

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "model-route.schema.json"


def test_route_matches_schema():
    document = build_model_route("drafting")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(document)) == []


def test_default_policy_is_task_specific():
    assert build_model_route("research")["policy"] == "balanced"
    assert build_model_route("drafting")["policy"] == "quality"
    assert build_model_route("editorial")["policy"] == "fast"


def test_selection_is_deterministic():
    assert build_model_route("drafting") == build_model_route("drafting")


def test_uses_injected_catalog_without_mutation():
    catalog = {
        "z-model": {"provider": "test", "capability": "quality", "available": True},
    }
    before = copy.deepcopy(catalog)
    route = build_model_route("drafting", catalog=catalog)
    assert route["model"] == "z-model"
    assert catalog == before


def test_unsupported_task_is_rejected():
    with pytest.raises(ValueError, match="Unsupported task"):
        build_model_route("translation")


def test_unavailable_models_are_not_selected():
    catalog = {
        "quality-model": {"provider": "test", "capability": "quality", "available": False},
    }
    with pytest.raises(ValueError, match="No available model"):
        build_model_route("drafting", catalog=catalog)


def test_missing_provider_is_rejected():
    catalog = {
        "quality-model": {"capability": "quality", "available": True},
    }
    with pytest.raises(ValueError, match="provider is missing"):
        build_model_route("drafting", catalog=catalog)


def test_route_has_no_network_access():
    assert build_model_route("research")["audit"]["network_access"] is False
