import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.details_to_include import build_details_to_include


def strategy(**overrides):
    value = {
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strategy-1",
        "schema_version": "1.0",
        "lifecycle_stage": "content_strategy_ready",
        "content_type": "guide",
        "evidence_refs": ["evidence-1"],
    }
    value.update(overrides)
    return value


def config(**overrides):
    value = {
        "config_id": "config-1",
        "brief_id": "brief-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strategy-1",
        "schema_version": "1.0",
        "lifecycle_stage": "article_config_ready",
        "article_type": "guide",
    }
    value.update(overrides)
    return value


def test_builds_default_details_contract():
    result = build_details_to_include(content_strategy=strategy(), article_config=config())
    assert result["lifecycle_stage"] == "details_to_include_ready"
    assert result["brief_id"] == "brief-1"
    assert result["details_to_include"]["key_takeaways"]["count"] == {"min": 3, "target": 4, "max": 5}
    assert result["details_to_include"]["quotes"]["source_requirement"] == "verified_source_evidence"
    assert result["details_to_include"]["bold"]["policy"] == "editorial_emphasis_only"


def test_details_contract_is_deterministic():
    first = build_details_to_include(content_strategy=strategy(), article_config=config())
    second = build_details_to_include(content_strategy=strategy(), article_config=config())
    assert first == second
    assert first["details_to_include_id"] == second["details_to_include_id"]


def test_details_contract_does_not_mutate_inputs():
    source = strategy()
    article = config()
    source_snapshot = copy.deepcopy(source)
    article_snapshot = copy.deepcopy(article)
    build_details_to_include(content_strategy=source, article_config=article)
    assert source == source_snapshot
    assert article == article_snapshot


def test_requires_ready_inputs():
    with pytest.raises(ValueError, match="content_strategy_ready"):
        build_details_to_include(content_strategy=strategy(lifecycle_stage="draft_ready"), article_config=config())
    with pytest.raises(ValueError, match="article_config_ready"):
        build_details_to_include(content_strategy=strategy(), article_config=config(lifecycle_stage="draft_ready"))


def test_requires_matching_lineage():
    with pytest.raises(ValueError, match="Lineage mismatch for report_id"):
        build_details_to_include(content_strategy=strategy(), article_config=config(report_id="other"))


def test_requires_matching_article_type():
    with pytest.raises(ValueError, match="Content type and article type must match"):
        build_details_to_include(content_strategy=strategy(content_type="comparison"), article_config=config(article_type="guide"))


def test_count_range_is_validated():
    details = {"key_takeaways": {"enabled": True, "required": True, "count": {"min": 5, "target": 3, "max": 6}}}
    with pytest.raises(ValueError, match="min <= target <= max"):
        build_details_to_include(content_strategy=strategy(), article_config=config(), details=details)


def test_required_feature_cannot_be_disabled():
    details = {"key_takeaways": {"enabled": False, "required": True, "count": {"min": 0, "target": 0, "max": 0}}}
    with pytest.raises(ValueError, match="required cannot be true"):
        build_details_to_include(content_strategy=strategy(), article_config=config(), details=details)


def test_disabled_feature_requires_zero_count():
    details = {"quotes": {"enabled": False, "required": False, "count": {"min": 1, "target": 1, "max": 2}}}
    with pytest.raises(ValueError, match="count must be zero"):
        build_details_to_include(content_strategy=strategy(), article_config=config(), details=details)


def test_required_feature_requires_nonzero_minimum():
    details = {"quotes": {"enabled": True, "required": True, "count": {"min": 0, "target": 1, "max": 2}}}
    with pytest.raises(ValueError, match="min must be at least 1"):
        build_details_to_include(content_strategy=strategy(), article_config=config(), details=details)


def test_quotes_are_gated_to_verified_source_evidence():
    details = {"quotes": {"enabled": True, "required": True, "count": {"min": 1, "target": 1, "max": 2}}}
    result = build_details_to_include(content_strategy=strategy(), article_config=config(), details=details)
    quotes = result["details_to_include"]["quotes"]
    assert quotes["source_requirement"] == "verified_source_evidence"
    assert quotes["attribution_required"] is True
    assert quotes["evidence_gate"] == "verified_evidence_required"


def test_bold_policy_is_editorial_only():
    result = build_details_to_include(content_strategy=strategy(), article_config=config())
    bold = result["details_to_include"]["bold"]
    assert bold["max_per_section"] == 3
    assert bold["policy"] == "editorial_emphasis_only"


def test_schema_validates_generated_contract():
    result = build_details_to_include(content_strategy=strategy(), article_config=config())
    schema = json.loads((Path(__file__).resolve().parents[1] / "shared" / "schemas" / "details-to-include.schema.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(result))
    assert errors == []


def test_contract_contains_no_prose_or_llm_invocation():
    result = build_details_to_include(content_strategy=strategy(), article_config=config())
    assert "body" not in result
    assert "quote" not in result["details_to_include"]["quotes"]
    assert "llm" not in result
    assert "provider" not in result
