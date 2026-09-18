from __future__ import annotations

from agents.intelligence.engine import build_intelligence
from agents.research.decision import build_decision
from agents.research.recommendation import build_recommendation


REPORT_ID = "rr_001"


def evidence(
    evidence_id: str,
    *,
    domain: str,
    value: str,
    relation: str = "supports",
    source_type: str = "local",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "report_id": REPORT_ID,
        "schema_version": "1.0",
        "type": "observation",
        "domain": domain,
        "subject": {"type": "keyword", "id": "consultant insurance"},
        "claim": {"type": "query_intent", "attribute": "primary_intent"},
        "value": {"type": "categorical", "data": value},
        "source": {
            "type": source_type,
            "source_id": evidence_id,
            "provider": "local",
            "retrieved_at": "2026-01-01T00:00:00Z",
        },
        "provenance": {
            "analyzer": "test",
            "analyzer_version": "1.0",
            "method": "fixture",
        },
        "confidence": 0.9,
        "relation": relation,
        "derived_from": [],
        "captured_at": "2026-01-01T00:00:00Z",
        "status": "active",
    }


def report() -> dict:
    return {
        "report_id": REPORT_ID,
        "schema_version": "1.0",
        "lifecycle_stage": "research_complete",
        "search_intent": {
            "keyword": "consultant insurance",
            "primary_intent": "commercial",
            "confidence": 0.9,
        },
        "evidence_refs": {
            "intent": ["ev_intent"],
            "entity": ["ev_entity"],
            "question": [],
            "business": ["ev_business"],
            "authority": ["ev_authority"],
        },
        "recommendation": None,
        "decision": None,
    }


def evidence_set() -> list[dict]:
    return [
        evidence("ev_intent", domain="intent", value="commercial", source_type="query"),
        evidence("ev_entity", domain="entity", value="consultant", source_type="serp"),
        evidence("ev_business", domain="business", value="commercial", source_type="business"),
        evidence("ev_authority", domain="authority", value="strong", source_type="authority"),
    ]


def test_intelligence_is_upstream_and_does_not_own_recommendation() -> None:
    research = report()
    intelligence = build_intelligence(research, evidence_set())

    assert intelligence["report_id"] == REPORT_ID
    assert intelligence["lifecycle_stage"] == "intelligence_ready"

    for field in ("recommendation_id", "decision_id", "strategy_id"):
        assert field not in intelligence

    recommendation = build_recommendation(research)
    assert recommendation["report_id"] == REPORT_ID
    assert recommendation["recommendation_id"]
    assert "intelligence_id" not in recommendation


def test_recommendation_owns_recommendation_lineage_before_decision() -> None:
    research = report()
    recommendation = build_recommendation(research)

    decision = build_decision(
        research_report=research,
        recommendation=recommendation,
    )

    assert decision["report_id"] == REPORT_ID
    assert decision["recommendation_id"] == recommendation["recommendation_id"]
    assert decision["recommendation_ref"] == recommendation["recommendation_id"]
    assert "intelligence_id" not in decision


def test_intelligence_and_recommendation_share_report_lineage_without_ownership_transfer() -> None:
    research = report()
    intelligence = build_intelligence(research, evidence_set())
    recommendation = build_recommendation(research)

    assert intelligence["report_id"] == recommendation["report_id"] == REPORT_ID
    assert intelligence["intelligence_id"] != recommendation["recommendation_id"]
    assert "recommendation_id" not in intelligence
    assert "intelligence_id" not in recommendation
