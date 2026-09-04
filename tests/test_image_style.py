from __future__ import annotations

import copy

import pytest

from agents.research.image_style import build_image_style


LINEAGE = {
    "brief_id": "brief_1",
    "report_id": "report_1",
    "decision_id": "decision_1",
    "strategy_id": "strategy_1",
    "config_id": "config_1",
    "draft_id": "draft_1",
    "image_spec_id": "imgspec_1",
}


def _spec() -> dict:
    return {
        **LINEAGE,
        "schema_version": "1.0",
        "lifecycle_stage": "ai_image_spec_ready",
        "images": [
            {
                "image_id": "image_1",
                "image_type": "hero",
                "section_index": 0,
                "section_heading": "Introduction",
                "purpose": "Establish the topic visually.",
                "prompt": "Create a professional editorial insurance illustration.",
                "aspect_ratio": "16:9",
                "width": 1600,
                "height": 900,
                "placement": "hero",
                "alt_text_status": "pending",
            },
            {
                "image_id": "image_2",
                "image_type": "section",
                "section_index": 1,
                "section_heading": "Coverage and Key Factors",
                "purpose": "Support the key concept.",
                "prompt": "Illustrate insurance coverage and key factors.",
                "aspect_ratio": "16:9",
                "width": 1600,
                "height": 900,
                "placement": "section",
                "alt_text_status": "pending",
            },
        ],
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "brand_style_included": False,
            "media_strategy_included": False,
        },
        "audit": {"method": "test", "version": "v1", "validation_status": "validated"},
    }


def test_engine_output_has_expected_contract_shape():
    result = build_image_style(ai_image_spec=_spec())
    assert result["lifecycle_stage"] == "image_style_ready"
    assert result["image_spec_id"] == "imgspec_1"
    assert result["brand" if False else "visual_style"]["brand"] == "Insurance Review Lab"
    assert len(result["styled_images"]) == 2


def test_brand_palette_is_explicit():
    palette = build_image_style(ai_image_spec=_spec())["visual_style"]["color_palette"]
    assert palette == {
        "deep_navy": "#0F172A",
        "modern_blue": "#2563EB",
        "cyan_accent": "#06B6D4",
        "white": "#FFFFFF",
    }


def test_style_is_applied_to_each_image():
    result = build_image_style(ai_image_spec=_spec())
    first = result["styled_images"][0]["styled_prompt"]
    assert "Insurance Review Lab" in first
    assert "#0F172A" in first
    assert "premium editorial illustration" in first
    assert "no watermark" in first


def test_image_identity_and_lineage_are_preserved():
    result = build_image_style(ai_image_spec=_spec())
    assert [item["image_id"] for item in result["styled_images"]] == ["image_1", "image_2"]
    for field, value in LINEAGE.items():
        assert result[field] == value


def test_engine_is_deterministic():
    assert build_image_style(ai_image_spec=_spec()) == build_image_style(ai_image_spec=_spec())


def test_engine_does_not_mutate_source():
    source = _spec()
    before = copy.deepcopy(source)
    build_image_style(ai_image_spec=source)
    assert source == before


def test_engine_excludes_generation_and_media_strategy():
    result = build_image_style(ai_image_spec=_spec())
    assert result["constraints"] == {
        "network_access": False,
        "provider_call": False,
        "image_analysis_call": False,
        "media_strategy_included": False,
        "source_mutation": False,
    }


def test_engine_requires_ready_image_spec():
    source = _spec()
    source["lifecycle_stage"] = "invalid"
    with pytest.raises(ValueError, match="ai_image_spec_ready"):
        build_image_style(ai_image_spec=source)


def test_engine_requires_image_identity_and_prompt():
    source = _spec()
    del source["images"][0]["prompt"]
    with pytest.raises(ValueError, match="prompt"):
        build_image_style(ai_image_spec=source)


def test_engine_rejects_invalid_image_type():
    source = _spec()
    source["images"][0]["image_type"] = "photo"
    with pytest.raises(ValueError, match="unsupported image_type"):
        build_image_style(ai_image_spec=source)
