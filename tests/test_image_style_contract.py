from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agents.research.image_style import build_image_style

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "image-style.schema.json"


def _valid_contract() -> dict:
    style = {
        "brand": "Insurance Review Lab",
        "palette": {"deep_navy": "#0F172A", "modern_blue": "#2563EB", "cyan_accent": "#06B6D4", "white": "#FFFFFF"},
        "visual_language": ["professional", "editorial", "research-oriented", "clean", "modern", "trustworthy"],
        "composition": ["clear focal point", "structured composition", "generous whitespace", "restrained visual hierarchy"],
        "illustration_direction": ["premium editorial illustration", "clean geometric elements", "subtle analytical/data motifs"],
        "restrictions": ["no watermark", "no unnecessary text", "no logos", "no visual clutter", "no off-brand colors", "no misleading imagery"],
    }
    return {
        "image_style_id": "imgstyle_1234567890abcdef", "brief_id": "brief_1", "report_id": "report_1",
        "decision_id": "decision_1", "strategy_id": "strategy_1", "config_id": "config_1", "draft_id": "draft_1",
        "image_spec_id": "imgspec_1", "schema_version": "1.0", "lifecycle_stage": "image_style_ready",
        "visual_style": style,
        "styled_images": [{
            "image_id": "image_1", "section_index": 0, "section_heading": "Introduction",
            "image_type": "hero", "styled_prompt": "Editorial insurance illustration. Apply Insurance Review Lab visual style."
        }],
        "constraints": {"network_access": False, "provider_call": False, "image_analysis_call": False, "media_strategy_included": False, "source_mutation": False},
        "audit": {"method": "ai_image_spec_to_brand_visual_style", "version": "v1", "validation_status": "validated"},
    }


def _validate(document: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(document))


def test_valid_contract_matches_schema():
    assert _validate(_valid_contract()) == []


def test_brand_palette_is_fixed():
    document = _valid_contract()
    document["visual_style"]["palette"]["modern_blue"] = "#000000"
    assert _validate(document)


def test_brand_name_is_fixed():
    document = _valid_contract()
    document["visual_style"]["brand"] = "Other Brand"
    assert _validate(document)


def test_lifecycle_is_fixed():
    document = _valid_contract()
    document["lifecycle_stage"] = "ai_image_spec_ready"
    assert _validate(document)


def test_media_strategy_is_explicitly_excluded():
    document = _valid_contract()
    document["constraints"]["media_strategy_included"] = True
    assert _validate(document)


def test_provider_and_network_access_are_forbidden():
    document = _valid_contract()
    document["constraints"]["provider_call"] = True
    assert _validate(document)


def test_unknown_properties_are_rejected():
    document = _valid_contract()
    document["provider"] = "image-api"
    assert _validate(document)


def test_styled_images_are_required_and_non_empty():
    document = _valid_contract()
    document["styled_images"] = []
    assert _validate(document)


def test_contract_fixture_can_be_copied_without_mutation():
    document = _valid_contract()
    before = copy.deepcopy(document)
    assert _validate(document) == []
    assert document == before


def test_engine_builds_schema_valid_contract():
    spec = _valid_contract()
    result = build_image_style(ai_image_spec={
        "brief_id": spec["brief_id"], "report_id": spec["report_id"], "decision_id": spec["decision_id"],
        "strategy_id": spec["strategy_id"], "config_id": spec["config_id"], "draft_id": spec["draft_id"],
        "image_spec_id": spec["image_spec_id"], "schema_version": "1.0", "lifecycle_stage": "ai_image_spec_ready",
        "images": [{"image_id": "image_1", "image_type": "hero", "section_index": 0, "section_heading": "Introduction",
                    "purpose": "Intro", "prompt": "Editorial insurance illustration.", "aspect_ratio": "16:9",
                    "width": 1600, "height": 900, "placement": "hero", "alt_text_status": "pending"}],
    })
    assert _validate(result) == []
