from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.ai_images import build_ai_image_spec

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
        "images": [{
            "image_id": "image_1234567890abcdef", "image_type": "hero", "section_index": 0,
            "section_heading": "Introduction", "purpose": "Establish the article topic visually.",
            "prompt": "Editorial insurance illustration about the article topic.", "aspect_ratio": "16:9",
            "width": 1600, "height": 900, "placement": "hero", "alt_text_status": "pending",
        }],
        "constraints": {"network_access": False, "provider_call": False, "brand_style_included": False, "media_strategy_included": False},
        "audit": {"method": "article_context_to_ai_image_specification", "version": "v1", "validation_status": "validated"},
    }


def _validate(document: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(document))


def _upstream() -> tuple[dict, dict, dict]:
    strategy = {
        "brief_id": "brief_1", "report_id": "report_1", "decision_id": "decision_1", "strategy_id": "strategy_1",
        "schema_version": "1.0", "lifecycle_stage": "content_strategy_ready", "content_type": "guide",
        "primary_keyword": "consultant insurance", "audience": "US consultants", "angle": "coverage and cost",
        "format": "guide", "sections": ["Introduction", "Professional Liability Coverage", "Cost"],
        "evidence_refs": ["ev_1"], "audit": {"method": "test", "version": "v1", "validation_status": "validated"},
    }
    config = {
        "config_id": "config_1", "brief_id": "brief_1", "report_id": "report_1", "decision_id": "decision_1", "strategy_id": "strategy_1",
        "schema_version": "1.0", "lifecycle_stage": "article_config_ready", "article_type": "guide", "article_size": "standard",
        "target_country": "US", "word_target": {"min": 1000, "target": 1500, "max": 2000},
        "heading_target": {"min": 5, "target": 7, "max": 10}, "h3_target": {"min": 2, "target": 4, "max": 6},
        "audit": {"method": "test", "version": "v1", "validation_status": "validated", "target_policy": "explicit_country_required"},
    }
    draft = {
        "draft_id": "draft_1", "brief_id": "brief_1", "report_id": "report_1", "decision_id": "decision_1", "strategy_id": "strategy_1",
        "schema_version": "1.0", "lifecycle_stage": "draft_ready", "title": "Consultant Insurance Guide",
        "content_type": "guide", "primary_keyword": "consultant insurance",
        "sections": [
            {"heading": "Introduction", "body": "Body", "purpose": "Intro", "evidence_refs": ["ev_1"], "claims": [{"claim_id": "c1", "text": "Claim", "evidence_refs": ["ev_1"], "grounding_status": "grounded"}]},
            {"heading": "Professional Liability Coverage", "body": "Body", "purpose": "Coverage", "evidence_refs": ["ev_1"], "claims": [{"claim_id": "c2", "text": "Claim", "evidence_refs": ["ev_1"], "grounding_status": "grounded"}]},
            {"heading": "Cost", "body": "Body", "purpose": "Cost", "evidence_refs": ["ev_1"], "claims": [{"claim_id": "c3", "text": "Claim", "evidence_refs": ["ev_1"], "grounding_status": "grounded"}]},
        ],
        "evidence_refs": ["ev_1"], "editorial_constraints": [],
        "audit": {"method": "test", "version": "v1", "validation_status": "validated"},
    }
    return strategy, config, draft


def test_valid_contract_matches_schema():
    assert _validate(_valid_contract()) == []


def test_required_upstream_lineage_is_enforced():
    document = _valid_contract(); del document["strategy_id"]
    assert _validate(document)


def test_images_are_required_and_non_empty():
    document = _valid_contract(); document["images"] = []
    assert _validate(document)


def test_supported_image_types_are_enforced():
    document = _valid_contract(); document["images"][0]["image_type"] = "thumbnail"
    assert _validate(document)


def test_supported_aspect_ratios_are_enforced():
    document = _valid_contract(); document["images"][0]["aspect_ratio"] = "3:2"
    assert _validate(document)


def test_alt_text_is_deferred_to_phase_nine():
    document = _valid_contract(); document["images"][0]["alt_text_status"] = "ready"
    assert _validate(document)


def test_brand_style_and_media_strategy_are_not_part_of_v1():
    document = _valid_contract(); document["constraints"]["brand_style_included"] = True
    assert _validate(document)


def test_network_and_provider_calls_are_forbidden_in_contract_v1():
    document = _valid_contract(); document["constraints"]["network_access"] = True
    assert _validate(document)


def test_unknown_properties_are_rejected():
    document = _valid_contract(); document["provider"] = "some-image-api"
    assert _validate(document)


def test_contract_fixture_can_be_copied_without_mutation():
    document = _valid_contract(); before = copy.deepcopy(document)
    assert _validate(document) == []
    assert document == before


def test_engine_builds_schema_valid_specification():
    strategy, config, draft = _upstream()
    result = build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)
    assert _validate(result) == []
    assert result["lifecycle_stage"] == "ai_image_spec_ready"
    assert len(result["images"]) == 3


def test_engine_preserves_lineage_and_config_draft_ids():
    strategy, config, draft = _upstream()
    result = build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)
    for field in ("brief_id", "report_id", "decision_id", "strategy_id"):
        assert result[field] == strategy[field] == config[field] == draft[field]
    assert result["config_id"] == config["config_id"]
    assert result["draft_id"] == draft["draft_id"]


@pytest.mark.parametrize("artifact, lifecycle", [
    ("strategy", "wrong"), ("config", "wrong"), ("draft", "wrong"),
])
def test_engine_requires_ready_upstream_lifecycles(artifact, lifecycle):
    strategy, config, draft = _upstream()
    {"strategy": strategy, "config": config, "draft": draft}[artifact]["lifecycle_stage"] = lifecycle
    with pytest.raises(ValueError):
        build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)


def test_engine_rejects_lineage_mismatch():
    strategy, config, draft = _upstream()
    draft["report_id"] = "report_other"
    with pytest.raises(ValueError, match="lineage mismatch"):
        build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)


def test_engine_is_deterministic():
    strategy, config, draft = _upstream()
    first = build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)
    second = build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)
    assert first == second


def test_engine_does_not_mutate_inputs():
    strategy, config, draft = _upstream()
    before = (copy.deepcopy(strategy), copy.deepcopy(config), copy.deepcopy(draft))
    build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)
    assert (strategy, config, draft) == before


def test_engine_defers_brand_media_alt_and_provider_concerns():
    strategy, config, draft = _upstream()
    result = build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)
    assert result["constraints"] == {
        "network_access": False, "provider_call": False,
        "brand_style_included": False, "media_strategy_included": False,
    }
    assert all(image["alt_text_status"] == "pending" for image in result["images"])


def test_engine_maps_first_section_to_hero_and_following_sections_to_section_images():
    strategy, config, draft = _upstream()
    result = build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)
    assert result["images"][0]["image_type"] == "hero"
    assert result["images"][0]["placement"] == "hero"
    assert all(image["image_type"] == "section" for image in result["images"][1:])
    assert all(image["placement"] == "section" for image in result["images"][1:])


def test_engine_rejects_missing_strategy_sections():
    strategy, config, draft = _upstream(); strategy["sections"] = []
    with pytest.raises(ValueError, match="sections"):
        build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)


def test_engine_rejects_draft_without_sections():
    strategy, config, draft = _upstream(); draft["sections"] = []
    with pytest.raises(ValueError, match="sections"):
        build_ai_image_spec(content_strategy=strategy, article_config=config, article_draft=draft)
