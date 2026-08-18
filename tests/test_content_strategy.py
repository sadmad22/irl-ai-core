import json

import pytest
from jsonschema import validate

from agents.research.content_strategy import build_content_strategy


def approved_report():
    return {
        "report_id": "rr_content",
        "lifecycle_stage": "research_complete",
        "keyword": "expat health insurance",
        "search_intent": {"primary_intent": "Commercial"},
        "entity_analysis": {"entities": [{"name": "Cigna Global"}, {"name": "Allianz Care"}]},
        "question_analysis": {"questions": ["What does expat health insurance cover?", "How much does it cost?"]},
        "business_analysis": {"commercial_value": "high"},
    }


def decision():
    return {
        "decision_id": "dec_123",
        "report_id": "rr_content",
        "lifecycle_stage": "decision_ready",
        "outcome": "approved",
        "evidence_refs": ["ev_intent", "ev_business", "ev_authority"],
    }


def test_builds_strategy_from_approved_decision():
    result = build_content_strategy(research_report=approved_report(), decision=decision())
    assert result["lifecycle_stage"] == "content_strategy_ready"
    assert result["report_id"] == "rr_content"
    assert result["decision_id"] == "dec_123"
    assert result["content_type"] == "comparison"
    assert result["primary_keyword"] == "expat health insurance"
    assert result["evidence_refs"] == ["ev_intent", "ev_business", "ev_authority"]
    assert "Cigna Global" in result["entities"]
    assert result["questions"]
    assert result["audit"]["method"] == "decision_to_content_strategy"


def test_strategy_is_deterministic():
    first = build_content_strategy(research_report=approved_report(), decision=decision())
    second = build_content_strategy(research_report=approved_report(), decision=decision())
    assert first == second


@pytest.mark.parametrize("outcome", ["rejected", "deferred"])
def test_strategy_rejects_non_approved_decision(outcome):
    rejected = decision() | {"outcome": outcome}
    with pytest.raises(ValueError, match="approved Decision"):
        build_content_strategy(research_report=approved_report(), decision=rejected)


def test_strategy_rejects_wrong_report_id():
    bad = decision() | {"report_id": "other"}
    with pytest.raises(ValueError, match="Decision.report_id"):
        build_content_strategy(research_report=approved_report(), decision=bad)


def test_strategy_rejects_non_decision_ready():
    bad = decision() | {"lifecycle_stage": "recommendation_ready"}
    with pytest.raises(ValueError, match="decision_ready"):
        build_content_strategy(research_report=approved_report(), decision=bad)


def test_contract_shape_is_strict():
    import pathlib
    schema_path = pathlib.Path("shared/schemas/content-strategy.schema.json")
    schema = json.loads(schema_path.read_text())
    result = build_content_strategy(research_report=approved_report(), decision=decision())
    validate(result, schema)
