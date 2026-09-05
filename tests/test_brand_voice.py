from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.brand_voice import build_brand_voice

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "brand-voice.schema.json"


def _inputs() -> tuple[dict, dict]:
    strategy = {
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strategy-1",
        "schema_version": "1.0",
        "lifecycle_stage": "content_strategy_ready",
        "content_type": "guide",
        "primary_keyword": "consultant insurance",
        "audience": "U.S. consultants",
        "angle": "practical coverage guidance",
        "format": "guide",
        "sections": ["Coverage", "Cost"],
        "evidence_refs": ["ref-1"],
    }
    config = {
        "config_id": "config-1",
        "brief_id": "brief-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strategy-1",
        "schema_version": "1.0",
        "lifecycle_stage": "article_config_ready",
        "article_type": "guide",
        "article_size": "standard",
        "target_country": "United States",
        "word_target": {"min": 1000, "target": 1500, "max": 2000},
        "heading_target": {"min": 5, "target": 8, "max": 12},
        "h3_target": {"min": 4, "target": 6, "max": 10},
        "audit": {
            "method": "test",
            "version": "v1",
            "validation_status": "validated",
            "target_policy": "explicit_country_required",
        },
    }
    return strategy, config


def test_brand_voice_matches_strict_schema():
    strategy, config = _inputs()
    document = build_brand_voice(content_strategy=strategy, article_config=config)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(document)) == []


def test_identity_and_archetype_are_irl_specific():
    strategy, config = _inputs()
    voice = build_brand_voice(content_strategy=strategy, article_config=config)["brand_voice"]
    assert voice["identity"]["name"] == "Insurance Review Lab"
    assert voice["identity"]["archetype"] == "trusted_research_advisor"
    assert voice["identity"]["reader_relationship"] == "advisor_not_salesperson"


def test_core_traits_match_master_definition():
    strategy, config = _inputs()
    traits = build_brand_voice(content_strategy=strategy, article_config=config)["brand_voice"]["core_traits"]
    assert traits == ["calm", "confident", "clear", "practical", "evidence_aware", "human"]


def test_brand_voice_contains_editorial_and_insurance_rules():
    strategy, config = _inputs()
    voice = build_brand_voice(content_strategy=strategy, article_config=config)["brand_voice"]
    assert "explain before recommending" in voice["editorial_principles"]
    assert "compare before concluding" in voice["editorial_principles"]
    assert "Distinguish coverage from exclusions." in voice["insurance_language_rules"]
    assert "Do not present estimates as universal prices." in voice["insurance_language_rules"]


def test_promotional_boundaries_are_non_promotional():
    strategy, config = _inputs()
    boundaries = build_brand_voice(content_strategy=strategy, article_config=config)["brand_voice"]["promotional_boundaries"]
    assert boundaries["position"] == "non_promotional"
    assert "hard selling" in boundaries["avoid"]
    assert "fear-based messaging" in boundaries["avoid"]
    assert "unsupported superlatives" in boundaries["avoid"]


def test_confidence_policy_requires_evidence_aware_qualification():
    strategy, config = _inputs()
    policy = build_brand_voice(content_strategy=strategy, article_config=config)["brand_voice"]["confidence_policy"]
    assert "evidence supports" in policy["principle"]
    assert "may" in policy["preferred_qualifiers"]
    assert "depending on" in policy["preferred_qualifiers"]
    assert "Never manufacture certainty." == policy["prohibited_behavior"]


def test_llm_guidance_is_explicit_but_core_does_not_invoke_llm():
    strategy, config = _inputs()
    document = build_brand_voice(content_strategy=strategy, article_config=config)
    assert document["llm_guidance"]["apply_to"] == ["drafting", "revision", "editorial"]
    assert document["constraints"]["llm_invocation"] is False
    assert document["constraints"]["provider_call"] is False
    assert document["constraints"]["network_access"] is False


def test_lineage_is_preserved():
    strategy, config = _inputs()
    document = build_brand_voice(content_strategy=strategy, article_config=config)
    assert document["brief_id"] == "brief-1"
    assert document["report_id"] == "report-1"
    assert document["decision_id"] == "decision-1"
    assert document["strategy_id"] == "strategy-1"
    assert document["config_id"] == "config-1"


def test_lineage_mismatch_is_rejected():
    strategy, config = _inputs()
    config["strategy_id"] = "different"
    with pytest.raises(ValueError, match="Lineage mismatch"):
        build_brand_voice(content_strategy=strategy, article_config=config)


def test_wrong_lifecycle_is_rejected():
    strategy, config = _inputs()
    strategy["lifecycle_stage"] = "draft_ready"
    with pytest.raises(ValueError, match="requires content_strategy_ready"):
        build_brand_voice(content_strategy=strategy, article_config=config)


def test_content_type_and_article_type_must_match():
    strategy, config = _inputs()
    config["article_type"] = "comparison"
    with pytest.raises(ValueError, match="must match"):
        build_brand_voice(content_strategy=strategy, article_config=config)


def test_invalid_content_type_is_rejected():
    strategy, config = _inputs()
    strategy["content_type"] = "review"
    with pytest.raises(ValueError, match="Unsupported content strategy content_type"):
        build_brand_voice(content_strategy=strategy, article_config=config)


def test_brand_voice_is_deterministic():
    strategy, config = _inputs()
    first = build_brand_voice(content_strategy=strategy, article_config=config)
    second = build_brand_voice(content_strategy=strategy, article_config=config)
    assert first == second


def test_inputs_are_not_mutated():
    strategy, config = _inputs()
    strategy_before = copy.deepcopy(strategy)
    config_before = copy.deepcopy(config)
    build_brand_voice(content_strategy=strategy, article_config=config)
    assert strategy == strategy_before
    assert config == config_before


def test_route_id_changes_when_lineage_changes():
    strategy, config = _inputs()
    first = build_brand_voice(content_strategy=strategy, article_config=config)["brand_voice_id"]
    config["config_id"] = "config-2"
    second = build_brand_voice(content_strategy=strategy, article_config=config)["brand_voice_id"]
    assert first != second


def test_schema_rejects_unexpected_property():
    strategy, config = _inputs()
    document = build_brand_voice(content_strategy=strategy, article_config=config)
    document["unexpected"] = True
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(document))
