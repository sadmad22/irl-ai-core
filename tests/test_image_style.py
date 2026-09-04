from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.image_style import build_image_style

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "image-style.schema.json"


def _spec() -> dict:
    return {
        "image_spec_id": "imgspec_1234567890abcdef",
        "brief_id": "brief_1", "report_id": "report_1", "decision_id": "decision_1", "strategy_id": "strategy_1",
        "config_id": "config_1", "draft_id": "draft_1", "schema_version": "1.0", "lifecycle_stage": "ai_image_spec_ready",
        "images": [
            {"image_id": "image_1", "image_type": "hero", "section_index": 0, "section_heading": "Introduction", "purpose": "Establish the topic", "prompt": "Create a professional insurance illustration.", "aspect_ratio": "16:9", "width": 1600, "height": 900, "placement": "hero", "alt_text_status": "pending"},
            {"image_id": "image_2", "image_type": "section", "section_index": 1, "section_heading": "Coverage", "purpose": "Explain coverage", "prompt": "Illustrate professional liability coverage.", "aspect_ratio": "16:9", "width": 1600, "height": 900, "placement": "section", "alt_text_status": "pending"},
        ],
        "constraints": {"network_access": False, "provider_call": False, "brand_style_included": False, "media_strategy_included": False},
        "audit": {"method": "article_context_to_ai_image_specification", "version": "v1", "validation_status": "validated"},
    }


def _validate(document: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(document))


def test_schema_accepts_valid_engine_output():
    result = build_image_style(ai_image_spec=_spec())
    assert _validate(result) == []


def test_output_shape_and_lifecycle_are_explicit():
    result = build_image_style(ai_image_spec=_spec())
    assert result["lifecycle_stage"] == "image_style_ready"
    assert result["schema_version"] == "1.0"
    assert result["image_style_id"].startswith("imgstyle_")
    assert len(result["styled_images"]) == 2


def test_brand_palette_is_explicit():
    style = build_image_style(ai_image_spec=_spec())["visual_style"]
    assert style["brand"] == "Insurance Review Lab"
    assert style["palette"] == {"deep_navy": "#0F172A", "modern_blue": "#2563EB", "cyan_accent": "#06B6D4", "white": "#FFFFFF"}


def test_style_is_applied_to_every_image_prompt():
    result = build_image_style(ai_image_spec=_spec())
    for image in result["styled_images"]:
        assert "Insurance Review Lab" in image["styled_prompt"]
        assert "#0F172A" in image["styled_prompt"]
        assert "#2563EB" in image["styled_prompt"]
        assert "#06B6D4" in image["styled_prompt"]
        assert "no watermark" in image["styled_prompt"]


def test_lineage_and_image_identity_are_preserved():
    source = _spec()
    result = build_image_style(ai_image_spec=source)
    for field in ("brief_id", "report_id", "decision_id", "strategy_id", "config_id", "draft_id", "image_spec_id"):
        assert result[field] == source[field]
    assert [item["image_id"] for item in result["styled_images"]] == ["image_1", "image_2"]


def test_engine_is_deterministic():
    source = _spec()
    assert build_image_style(ai_image_spec=source) == build_image_style(ai_image_spec=source)


def test_engine_does_not_mutate_source():
    source = _spec()
    before = copy.deepcopy(source)
    build_image_style(ai_image_spec=source)
    assert source == before


def test_generation_provider_and_media_strategy_are_excluded():
    result = build_image_style(ai_image_spec=_spec())
    assert result["constraints"] == {"network_access": False, "provider_call": False, "image_analysis_call": False, "media_strategy_included": False, "source_mutation": False}


def test_ready_image_spec_is_required():
    source = _spec()
    source["lifecycle_stage"] = "wrong"
    with pytest.raises(ValueError, match="ai_image_spec_ready"):
        build_image_style(ai_image_spec=source)


def test_image_identity_and_prompt_are_required():
    source = _spec()
    del source["images"][0]["image_id"]
    with pytest.raises(ValueError, match="image_id"):
        build_image_style(ai_image_spec=source)


def test_invalid_image_type_is_rejected():
    source = _spec()
    source["images"][0]["image_type"] = "thumbnail"
    with pytest.raises(ValueError, match="Unsupported AI image type"):
        build_image_style(ai_image_spec=source)


def test_lineage_fields_are_required():
    source = _spec()
    del source["image_spec_id"]
    with pytest.raises(ValueError, match="image_spec_id"):
        build_image_style(ai_image_spec=source)
