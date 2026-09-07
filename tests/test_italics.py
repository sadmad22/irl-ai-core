import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from agents.research.italics import build_italics_contract


def outline():
    return {
        "outline_editor_id": "outline-1",
        "brief_id": "brief-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strat-1",
        "config_id": "config-1",
        "structure_id": "structure-1",
        "details_to_include_id": "details-1",
        "schema_version": "1.0",
        "lifecycle_stage": "outline_editor_ready",
        "article_type": "guide",
        "primary_keyword": "consultant insurance",
        "sections": [{"order": 1, "heading": "Introduction", "level": "H2", "required": True}],
        "constraints": {"h3": {"min": 0, "max": 1}},
        "audit": {"method": "content_strategy_to_outline_editor", "method_version": "v1", "validation_status": "validated"},
    }


def test_default_italics_contract_is_disabled_and_deterministic():
    first = build_italics_contract(outline_editor=outline())
    second = build_italics_contract(outline_editor=outline())
    assert first == second
    assert first["italics"] == {"enabled": False, "required": False, "max_per_section": 0, "policy": "editorial_emphasis_only"}
    assert first["lifecycle_stage"] == "italics_ready"


def test_enabled_italics_preserves_editorial_configuration():
    result = build_italics_contract(
        outline_editor=outline(),
        italics={"enabled": True, "required": False, "max_per_section": 2},
    )
    assert result["italics"] == {"enabled": True, "required": False, "max_per_section": 2, "policy": "editorial_emphasis_only"}


def test_required_cannot_be_disabled():
    with pytest.raises(ValueError, match="required cannot be true when disabled"):
        build_italics_contract(outline_editor=outline(), italics={"enabled": False, "required": True, "max_per_section": 0})


def test_disabled_italics_must_have_zero_maximum():
    with pytest.raises(ValueError, match="disabled feature max_per_section"):
        build_italics_contract(outline_editor=outline(), italics={"enabled": False, "required": False, "max_per_section": 1})


def test_enabled_italics_requires_positive_maximum():
    with pytest.raises(ValueError, match="at least 1"):
        build_italics_contract(outline_editor=outline(), italics={"enabled": True, "required": False, "max_per_section": 0})


def test_rejects_non_editorial_policy():
    with pytest.raises(ValueError, match="editorial_emphasis_only"):
        build_italics_contract(outline_editor=outline(), italics={"enabled": True, "required": False, "max_per_section": 1, "policy": "seo_keyword_emphasis"})


def test_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unsupported fields"):
        build_italics_contract(outline_editor=outline(), italics={"enabled": True, "required": False, "max_per_section": 1, "unexpected": True})


def test_rejects_wrong_outline_lifecycle():
    source = outline()
    source["lifecycle_stage"] = "article_structure_ready"
    with pytest.raises(ValueError, match="outline_editor_ready"):
        build_italics_contract(outline_editor=source)


def test_does_not_mutate_inputs():
    source = outline()
    settings = {"enabled": True, "required": False, "max_per_section": 2}
    before_source = copy.deepcopy(source)
    before_settings = copy.deepcopy(settings)
    build_italics_contract(outline_editor=source, italics=settings)
    assert source == before_source
    assert settings == before_settings


def test_output_validates_against_schema():
    output = build_italics_contract(outline_editor=outline(), italics={"enabled": True, "required": False, "max_per_section": 2})
    schema = json.loads(Path("shared/schemas/italics.schema.json").read_text())
    Draft202012Validator(schema).validate(output)


def test_schema_rejects_unknown_nested_field():
    output = build_italics_contract(outline_editor=outline())
    output["italics"]["unexpected"] = True
    schema = json.loads(Path("shared/schemas/italics.schema.json").read_text())
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(output)


def test_no_prose_or_llm_fields():
    output = build_italics_contract(outline_editor=outline())
    forbidden = {"prompt", "llm", "provider", "model", "prose", "body", "generated_text", "text_spans"}
    assert forbidden.isdisjoint(output)
