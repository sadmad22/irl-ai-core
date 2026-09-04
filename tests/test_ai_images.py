from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "ai-image.schema.json"


def _valid_contract() -> dict:
    return {
        "image_spec_id": "imgspec_1234567890abcdef",
        "brief_id": "brief_1",
        "report_id": "report_1",
        "decision_id": "decision_1",
        "strategy_id": "strategy_1",
        "config_id": "config_1",
        "draft_id": "draft_1",
        "schema_version": "1.0",
        "lifecycle_stage": "ai_image_spec_ready",
        "images": [
            {
                "image_id": "image_1234567890abcdef",
                "image_type": "hero",
                "section_index": 0,
                "section_heading": "Introduction",
                "purpose": "Establish the article topic visually.",
                "prompt": "Editorial insurance illustration about the article topic.",
                "aspect_ratio": "16:9",
                "width": 1600,
                "height": 900,
                "placement": "hero",
                "alt_text_status": "pending",
            }
        ],
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "brand_style_included": False,
            "media_strategy_included": False,
        },
        "audit": {
            "method": "article_context_to_ai_image_specification",
            "version": "v1",
            "validation_status": "validated",
        },
    }


def _validate(document: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(document))


def test_valid_contract_matches_schema():
    assert _validate(_valid_contract()) == []


def test_required_upstream_lineage_is_enforced():
    document = _valid_contract()
    del document["strategy_id"]
    assert _validate(document)


def test_images_are_required_and_non_empty():
    document = _valid_contract()
    document["images"] = []
    assert _validate(document)


def test_supported_image_types_are_enforced():
    document = _valid_contract()
    document["images"][0]["image_type"] = "thumbnail"
    assert _validate(document)


def test_supported_aspect_ratios_are_enforced():
    document = _valid_contract()
    document["images"][0]["aspect_ratio"] = "3:2"
    assert _validate(document)


def test_alt_text_is_deferred_to_phase_nine():
    document = _valid_contract()
    document["images"][0]["alt_text_status"] = "ready"
    assert _validate(document)


def test_brand_style_and_media_strategy_are_not_part_of_v1():
    document = _valid_contract()
    document["constraints"]["brand_style_included"] = True
    assert _validate(document)


def test_network_and_provider_calls_are_forbidden_in_contract_v1():
    document = _valid_contract()
    document["constraints"]["network_access"] = True
    assert _validate(document)


def test_unknown_properties_are_rejected():
    document = _valid_contract()
    document["provider"] = "some-image-api"
    assert _validate(document)


def test_contract_fixture_can_be_copied_without_mutation():
    document = _valid_contract()
    before = copy.deepcopy(document)
    assert _validate(document) == []
    assert document == before
