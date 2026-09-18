from __future__ import annotations

from agents.intelligence.project_integration import build_intelligence_from_project
from agents.research import production_orchestrator as orchestrator


PROJECT = "expat-health-insurance"


def test_real_topic_builds_canonical_intelligence_without_mutating_research():
    intelligence = build_intelligence_from_project(PROJECT)

    assert intelligence["report_id"] == "rr_expat-health-insurance"
    assert intelligence["intelligence_id"].startswith("int_")
    assert intelligence["lifecycle_stage"] == "intelligence_ready"
    assert intelligence["intent_interpretation"]["evidence_refs"]
    assert intelligence["topic_signals"]
    assert intelligence["commercial_signals"]
    assert intelligence["decision_signals"]

    downstream_ids = (
        "recommendation_id",
        "decision_id",
        "strategy_id",
        "brief_id",
        "draft_id",
        "quality_id",
    )
    assert all(field not in intelligence for field in downstream_ids)


def test_real_topic_intelligence_is_accepted_as_canonical_orchestrator_stage():
    intelligence = build_intelligence_from_project(PROJECT)
    result = {
        "research_report": {"report_id": intelligence["report_id"]},
        "intelligence": intelligence,
        "content_brief": {"brief_id": "brief_123"},
    }

    assert orchestrator._completed_stages(result) == [
        "research",
        "intelligence",
        "configuration",
        "structure",
    ]


def test_content_brief_does_not_supply_intelligence_for_real_topic():
    result = {
        "research_report": {"report_id": "rr_expat-health-insurance"},
        "content_brief": {"brief_id": "brief_123"},
    }

    assert orchestrator._completed_stages(result) == [
        "research",
        "configuration",
        "structure",
    ]
