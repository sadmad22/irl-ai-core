from __future__ import annotations

import pytest

from agents.research.final_optimization import build_final_optimization

BASE_INPUTS = {
    "report": {"report_id": "report_001"},
    "decision": {"decision_id": "decision_001"},
    "strategy": {"strategy_id": "strategy_001"},
    "brief": {"brief_id": "brief_001"},
    "final_values": {
        "seo_title": "Consultant Liability Insurance Guide",
        "meta_description": "A practical guide to consultant liability insurance coverage and costs.",
        "primary_keyword": "consultant liability insurance",
        "slug": "consultant-liability-insurance",
    },
}


def build(inputs=BASE_INPUTS):
    return build_final_optimization(**inputs, method_version="v1")


def test_happy_path():
    artifact = build()
    assert artifact["schema_version"] == "1.0"
    assert artifact["method_version"] == "v1"
    assert artifact["lifecycle_stage"] == "optimization_ready"
    assert artifact["optimization_id"]
    assert artifact["seo_title"] == BASE_INPUTS["final_values"]["seo_title"]
    assert artifact["meta_description"] == BASE_INPUTS["final_values"]["meta_description"]
    assert artifact["primary_keyword"] == BASE_INPUTS["final_values"]["primary_keyword"]
    assert artifact["slug"] == BASE_INPUTS["final_values"]["slug"]
    assert artifact["lineage"] == {"report_id": "report_001", "decision_id": "decision_001", "strategy_id": "strategy_001", "brief_id": "brief_001"}

@pytest.mark.parametrize("field", ["seo_title", "meta_description", "primary_keyword", "slug"])
def test_required_final_value_missing_fails(field):
    values = {**BASE_INPUTS["final_values"]}
    values.pop(field)
    with pytest.raises((ValueError, KeyError)):
        build({**BASE_INPUTS, "final_values": values})

@pytest.mark.parametrize("field", ["seo_title", "meta_description", "primary_keyword", "slug"])
def test_required_final_value_whitespace_fails(field):
    values = {**BASE_INPUTS["final_values"], field: "   "}
    with pytest.raises(ValueError):
        build({**BASE_INPUTS, "final_values": values})

@pytest.mark.parametrize("field", ["report", "decision", "strategy", "brief"])
def test_required_lineage_source_missing_fails(field):
    with pytest.raises((ValueError, KeyError)):
        build({**BASE_INPUTS, field: {}})

def test_conflicting_lineage_fails_closed():
    with pytest.raises(ValueError):
        build({**BASE_INPUTS, "lineage": {"report_id": "different_report"}})

def test_invalid_lifecycle_fails_closed():
    with pytest.raises(ValueError):
        build({**BASE_INPUTS, "lifecycle_stage": "delivery_ready"})

def test_unsupported_downstream_fields_fail_closed():
    with pytest.raises(ValueError):
        build({**BASE_INPUTS, "extra": {"publish": True}})

def test_seo_validation_cannot_replace_optimization():
    inputs = {**BASE_INPUTS}
    inputs.pop("final_values")
    inputs["seo_validation"] = {"seo_title": "From Validation", "meta_description": "From validation"}
    with pytest.raises((ValueError, KeyError)):
        build(inputs)

def test_article_prose_cannot_supply_missing_values():
    inputs = {**BASE_INPUTS, "final_values": {"seo_title": "Explicit title"}, "article": {"body": "Hidden metadata source"}}
    with pytest.raises((ValueError, KeyError)):
        build(inputs)

def test_deterministic_identity_and_output():
    assert build() == build()

def test_optional_canonical_url_is_preserved():
    values = {**BASE_INPUTS["final_values"], "canonical_url": "https://example.com/consultant-liability-insurance"}
    artifact = build({**BASE_INPUTS, "final_values": values})
    assert artifact["canonical_url"] == values["canonical_url"]

def test_publication_intent_cannot_be_introduced():
    with pytest.raises(ValueError):
        build({**BASE_INPUTS, "production_intent": {"publish": True}})
