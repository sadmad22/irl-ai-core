from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.image_style import build_image_style

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "image-style.schema.json"


def _schema_errors(document: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(document))


def _spec() -> dict:
    return {
        "image_spec_id": "imgspec_1234567890abcdef", "brief_id": "brief_1", "report_id": "report_1",
        "decision_id": "decision_1", "strategy_id": "strategy_1", "config_id": "config_1", "draft_id": "draft_1",
        "schema_version": "1.0", "lifecycle_stage": "ai_image_spec_ready",
        "images": [{
            "image_id": "image_1234567890abcdef", "image_type": "hero", "section_index": 0,
            "section_heading": "Introduction", "purpose": "Establish topic", "prompt": "Editorial insurance illustration.",
            "aspect_ratio": "16:9", "width": 1600, "height": 900, "placement": "hero", "alt_text_status": "pending",
        }],
        "constraints": {"network_access": False, "provider_call": False, "brand_style_included": False, "media_strategy_included": False},
        "audit": {"method": "test", "version": "v1", "validation_status": "validated"},
    }


def test_engine_output_matches_schema():
    result = build_image_style(ai_image_spec=_spec())
    assert _schema_errors(result) == []


def test_brand_visual_system_is_explicit():
    style = build_image_style(ai_image_spec=_spec())["visual_style"]
    assert style["brand"] == "Insurance Review Lab"
    assert style["palette"] == {
        "deep_navy": "#0F172A", "modern_blue": "#2563EB", "cyan_accent": "#06B6D4", "white": "#FFFFFF"
    }
    assert "professional" in style["visual_language"]
    assert "premium editorial illustration" in style["illustration_direction"]


def test_style_is_applied_to_each_image_prompt():
    result = build_image_style(ai_image_spec=_spec())
    prompt = result["styled_images"][0]["styled_prompt"]
    assert "#0F172A" in prompt
    assert "#2563EB" in prompt
    assert "#06B6D4" in prompt
    assert "generous whitespace" in prompt
    assert "No watermark" in prompt


def test_lineage_and_image_identity_are_preserved():
    spec = _spec()
    result = build_image_style(ai_image_spec=spec)
    for field in ("brief_id", "report_id", "decision_id", "strategy_id", "config_id", "draft_id", "image_spec_id"):
        assert result[field] == spec[field]
    assert result["styled_images"][0]["image_id"] == spec["images"][0]["image_id"]


def test_engine_is_deterministic():
    spec = _spec()
    assert build_image_style(ai_image_spec=spec) == build_image_style(ai_image_spec=spec)


def test_engine_does_not_mutate_source():
    spec = _spec()
    before = copy.deepcopy(spec)
    build_image_style(ai_image_spec=spec)
    assert spec == before


def test_scope_excludes_generation_media_and_image_analysis():
    result = build_image_style(ai_image_spec=_spec())
    assert result["constraints"] == {
        "network_access": False, "provider_call": False, "image_analysis_call": False,
        "media_strategy_included": False, "source_mutation": False,
    }


def test_requires_ready_image_spec():
    spec = _spec()
    spec["lifecycle_stage"] = "draft_ready"
    with pytest.raises(ValueError, match="ai_image_spec_ready"):
        build_image_style(ai_image_spec=spec)


def test_requires_image_identity_heading_and_prompt():
    spec = _spec()
    del spec["images"][0]["image_id"]
    with pytest.raises(ValueError, match="image_id"):
        build_image_style(ai_image_spec=spec)


def test_rejects_unsupported_image_type():
    spec = _spec()
    spec["images"][0]["image_type"] = "thumbnail"
    with pytest.raises(ValueError, match="Unsupported AI image type"):
        build_image_style(ai_image_spec=spec)


def test_schema_rejects_generation_or_media_flags():
    document = build_image_style(ai_image_spec=_spec())
    document["constraints"]["provider_call"] = True
    assert _schema_errors(document)


def test_schema_rejects_unknown_properties():
    document = build_image_style(ai_image_spec=_spec())
    document["provider"] = "image-api"
    assert _schema_errors(document)
