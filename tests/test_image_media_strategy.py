from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.image_media_strategy import build_image_media_strategy

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "image-media-strategy.schema.json"


def _errors(document: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(document))


def _style() -> dict:
    return {
        "image_style_id": "imgstyle_1234567890abcdef", "brief_id": "brief_1", "report_id": "report_1",
        "decision_id": "decision_1", "strategy_id": "strategy_1", "config_id": "config_1", "draft_id": "draft_1",
        "image_spec_id": "imgspec_1", "schema_version": "1.0", "lifecycle_stage": "image_style_ready",
        "visual_style": {"brand": "Insurance Review Lab", "palette": {"deep_navy": "#0F172A", "modern_blue": "#2563EB", "cyan_accent": "#06B6D4", "white": "#FFFFFF"}, "visual_language": ["professional"], "composition": ["structured"], "illustration_direction": ["editorial"], "restrictions": ["no watermark"]},
        "styled_images": [
            {"image_id": "image_1", "section_index": 0, "section_heading": "Introduction", "image_type": "hero", "styled_prompt": "hero"},
            {"image_id": "image_2", "section_index": 1, "section_heading": "Coverage", "image_type": "infographic", "styled_prompt": "coverage"},
        ],
        "constraints": {"network_access": False, "provider_call": False, "image_analysis_call": False, "media_strategy_included": False, "source_mutation": False},
        "audit": {"method": "ai_image_spec_to_brand_visual_style", "version": "v1", "validation_status": "validated"},
    }


def test_engine_output_matches_schema():
    result = build_image_media_strategy(image_style=_style())
    assert _errors(result) == []


def test_lifecycle_and_lineage_are_preserved():
    source = _style()
    result = build_image_media_strategy(image_style=source)
    assert result["lifecycle_stage"] == "image_media_strategy_ready"
    for field in ("brief_id", "report_id", "decision_id", "strategy_id", "config_id", "draft_id", "image_spec_id", "image_style_id"):
        assert result[field] == source[field]


def test_hero_gets_hero_placement_and_role():
    result = build_image_media_strategy(image_style=_style())
    item = result["placements"][0]
    assert item["placement"] == "hero"
    assert item["media_role"] == "hero"


def test_infographic_gets_section_placement_and_explain_role():
    result = build_image_media_strategy(image_style=_style())
    item = result["placements"][1]
    assert item["placement"] == "section"
    assert item["media_role"] == "explain"


def test_section_image_gets_section_placement_and_illustrate_role():
    source = _style()
    source["styled_images"] = [
        {"image_id": "image_2", "section_index": 1, "section_heading": "Coverage", "image_type": "section", "styled_prompt": "coverage"},
        {"image_id": "image_3", "section_index": 2, "section_heading": "Claims", "image_type": "section", "styled_prompt": "claims"},
    ]
    result = build_image_media_strategy(image_style=source)
    assert result["placements"][0]["placement"] == "section"
    assert result["placements"][0]["media_role"] == "illustrate"
    assert result["placements"][1]["media_role"] == "illustrate"


def test_first_section_image_gets_support_role():
    source = _style()
    source["styled_images"] = [
        {"image_id": "image_2", "section_index": 0, "section_heading": "Coverage", "image_type": "section", "styled_prompt": "coverage"},
    ]
    result = build_image_media_strategy(image_style=source)
    assert result["placements"][0]["media_role"] == "support"


def test_comparison_gets_section_placement_and_compare_role():
    source = _style()
    source["styled_images"] = [
        {"image_id": "image_3", "section_index": 2, "section_heading": "Compare Plans", "image_type": "comparison", "styled_prompt": "comparison"},
    ]
    result = build_image_media_strategy(image_style=source)
    assert result["placements"][0]["placement"] == "section"
    assert result["placements"][0]["media_role"] == "compare"


def test_strategy_density_and_image_limit_are_deterministic():
    result = build_image_media_strategy(image_style=_style())
    assert result["strategy"] == {"density": "low", "max_images": 2, "hero_required": True, "avoid_repetition": True, "visual_breaks": True}


def test_engine_is_deterministic():
    source = _style()
    assert build_image_media_strategy(image_style=source) == build_image_media_strategy(image_style=source)


def test_engine_does_not_mutate_source():
    source = _style()
    before = copy.deepcopy(source)
    build_image_media_strategy(image_style=source)
    assert source == before


def test_requires_image_style_ready():
    source = _style()
    source["lifecycle_stage"] = "ai_image_spec_ready"
    with pytest.raises(ValueError, match="image_style_ready"):
        build_image_media_strategy(image_style=source)


def test_rejects_duplicate_image_ids():
    source = _style()
    source["styled_images"][1]["image_id"] = "image_1"
    with pytest.raises(ValueError, match="Duplicate"):
        build_image_media_strategy(image_style=source)


def test_rejects_invalid_section_index():
    source = _style()
    source["styled_images"][0]["section_index"] = -1
    with pytest.raises(ValueError, match="non-negative"):
        build_image_media_strategy(image_style=source)


def test_rejects_boolean_section_index():
    source = _style()
    source["styled_images"][0]["section_index"] = True
    with pytest.raises(ValueError, match="non-negative"):
        build_image_media_strategy(image_style=source)


def test_rejects_unknown_image_type():
    source = _style()
    source["styled_images"][0]["image_type"] = "thumbnail"
    with pytest.raises(ValueError, match="Unsupported"):
        build_image_media_strategy(image_style=source)


def test_scope_excludes_publishing_execution():
    result = build_image_media_strategy(image_style=_style())
    assert result["constraints"] == {"network_access": False, "provider_call": False, "wordpress_write": False, "media_upload": False, "html_generation": False, "source_mutation": False}


def test_schema_rejects_publishing_flags():
    result = build_image_media_strategy(image_style=_style())
    result["constraints"]["wordpress_write"] = True
    assert _errors(result)


def test_schema_rejects_unknown_properties():
    result = build_image_media_strategy(image_style=_style())
    result["provider"] = "wordpress"
    assert _errors(result)


def test_schema_rejects_invalid_placement_enum():
    result = build_image_media_strategy(image_style=_style())
    result["placements"][0]["placement"] = "between_sections"
    assert _errors(result)


def test_schema_rejects_empty_placements():
    result = build_image_media_strategy(image_style=_style())
    result["placements"] = []
    assert _errors(result)
