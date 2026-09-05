import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.tone_of_voice import build_tone_of_voice

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "shared/schemas/tone-of-voice.schema.json").read_text())


def strategy(**overrides):
    value = {
        "brief_id": "brief_1", "report_id": "report_1", "decision_id": "decision_1", "strategy_id": "strategy_1",
        "lifecycle_stage": "content_strategy_ready", "intent": "informational", "content_type": "guide"
    }
    value.update(overrides)
    return value


def config(**overrides):
    value = {
        "brief_id": "brief_1", "report_id": "report_1", "decision_id": "decision_1", "strategy_id": "strategy_1",
        "config_id": "config_1", "lifecycle_stage": "article_config_ready", "article_type": "guide"
    }
    value.update(overrides)
    return value


def test_valid_output_matches_schema():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    assert list(Draft202012Validator(SCHEMA).iter_errors(output)) == []


def test_lifecycle_and_lineage_preserved():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    assert output["lifecycle_stage"] == "tone_of_voice_ready"
    for key in ("brief_id", "report_id", "decision_id", "strategy_id", "config_id"):
        assert output[key] == (strategy()[key] if key != "config_id" else config()[key])


def test_guide_information_is_educational():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    assert output["tone"]["primary"] == "educational"
    assert output["tone"]["technicality"] == "moderate"


def test_comparison_is_analytical():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config(article_type="comparison"))
    assert output["tone"]["primary"] == "analytical"
    assert output["tone"]["technicality"] == "technical"


def test_buyer_guide_is_authoritative():
    output = build_tone_of_voice(content_strategy=strategy(intent="commercial"), article_config=config(article_type="buyer_guide"))
    assert output["tone"]["primary"] == "authoritative"


def test_tone_id_is_deterministic():
    first = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    second = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    assert first == second


def test_source_documents_are_not_mutated():
    source = strategy(); cfg = config()
    source_before = copy.deepcopy(source); cfg_before = copy.deepcopy(cfg)
    build_tone_of_voice(content_strategy=source, article_config=cfg)
    assert source == source_before
    assert cfg == cfg_before


def test_requires_ready_strategy():
    with pytest.raises(ValueError, match="content_strategy_ready"):
        build_tone_of_voice(content_strategy=strategy(lifecycle_stage="draft"), article_config=config())


def test_requires_ready_config():
    with pytest.raises(ValueError, match="article_config_ready"):
        build_tone_of_voice(content_strategy=strategy(), article_config=config(lifecycle_stage="draft"))


def test_rejects_lineage_mismatch():
    with pytest.raises(ValueError, match="Lineage mismatch"):
        build_tone_of_voice(content_strategy=strategy(), article_config=config(strategy_id="other"))


def test_rejects_invalid_intent():
    with pytest.raises(ValueError, match="Unsupported content strategy intent"):
        build_tone_of_voice(content_strategy=strategy(intent="unknown"), article_config=config())


def test_schema_rejects_unknown_top_level_property():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    output["llm_call"] = True
    assert any("Additional properties" in error.message for error in Draft202012Validator(SCHEMA).iter_errors(output))


def test_schema_rejects_brand_voice_scope():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    output["constraints"]["brand_voice_included"] = True
    assert list(Draft202012Validator(SCHEMA).iter_errors(output))


def test_schema_rejects_invalid_primary_enum():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    output["tone"]["primary"] = "marketing"
    assert list(Draft202012Validator(SCHEMA).iter_errors(output))


def test_schema_rejects_empty_preferred_traits():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    output["editorial_guidance"]["preferred_traits"] = []
    assert list(Draft202012Validator(SCHEMA).iter_errors(output))


def test_execution_scope_excludes_network_provider_and_source_mutation():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    assert output["constraints"] == {
        "network_access": False, "provider_call": False, "brand_voice_included": False,
        "point_of_view_included": False, "source_mutation": False
    }


def test_reader_address_is_you():
    output = build_tone_of_voice(content_strategy=strategy(), article_config=config())
    assert output["editorial_guidance"]["reader_address"] == "you"
