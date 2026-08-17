import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agents.research.recommendation import build_recommendation

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "shared/schemas/recommendation.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def _report(**overrides):
    report = {
        "report_id": "rr_test",
        "schema_version": "1.0",
        "lifecycle_stage": "research_complete",
        "metadata": {},
        "keyword": {"keyword": "best expat health insurance"},
        "search_intent": {"primary_intent": "Commercial", "confidence": 0.8},
        "search_metrics": {},
        "serp_analysis": {"results": [{"position": i, "domain": f"site-{i}.example"} for i in range(1, 11)]},
        "competitor_analysis": {"domain_counts": {f"site-{i}.example": 1 for i in range(1, 11)}},
        "entity_analysis": {},
        "question_analysis": {},
        "topical_authority": {"authority_score": 0.9, "topic_fit": 0.9},
        "business_analysis": {"affiliate_potential": 0.9, "adsense_potential": 0.8, "conversion_potential": 0.8, "commercial_value": 0.9},
        "evidence_refs": {
            "intent": ["ev_intent"],
            "entity": ["ev_entity"],
            "question": ["ev_question"],
            "business": ["ev_business"],
            "authority": ["ev_authority"],
        },
        "recommendation": None,
        "decision": None,
        "audit": {"validation_status": "pending", "validation_errors": [], "notes": []},
    }
    report.update(overrides)
    return report


def test_recommendation_matches_contract_and_has_explicit_lineage():
    result = build_recommendation(_report())
    VALIDATOR.validate(result)
    assert result["recommendation"] == "pursue"
    assert result["content_type"] == "comparison"
    assert result["evidence_refs"] == ["ev_intent", "ev_entity", "ev_question", "ev_business", "ev_authority"]
    assert result["report_id"] == "rr_test"


def test_recommendation_is_deterministic():
    report = _report()
    first = build_recommendation(report)
    second = build_recommendation(report)
    assert first == second
    assert first["recommendation_id"] == second["recommendation_id"]


def test_incomplete_research_is_deferred():
    report = _report(
        evidence_refs={"intent": ["ev_intent"], "entity": [], "question": [], "business": [], "authority": []}
    )
    result = build_recommendation(report)
    assert result["recommendation"] == "defer"
    assert result["criteria"]["research_completeness"] == 0.2


def test_navigational_intent_is_rejected():
    report = _report(search_intent={"primary_intent": "Navigational", "confidence": 0.95})
    result = build_recommendation(report)
    assert result["recommendation"] == "reject"


def test_missing_report_id_is_rejected():
    report = _report(report_id="")
    try:
        build_recommendation(report)
    except ValueError as exc:
        assert "report_id" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_missing_evidence_lineage_is_rejected():
    report = _report(evidence_refs={"intent": [], "entity": [], "question": [], "business": [], "authority": []})
    try:
        build_recommendation(report)
    except ValueError as exc:
        assert "evidence_refs" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_wrong_lifecycle_stage_is_rejected():
    report = _report(lifecycle_stage="recommendation_ready")
    try:
        build_recommendation(report)
    except ValueError as exc:
        assert "research_complete" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
