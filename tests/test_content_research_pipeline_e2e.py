from __future__ import annotations

from agents.research.content_research_pipeline import build_content_research_to_wordpress_draft


def report():
    return {
        "report_id": "report_1",
        "lifecycle_stage": "research_complete",
        "keyword": "accountant insurance",
        "search_intent": {"primary_intent": "informational"},
        "entity_analysis": {"entities": [{"entity": "CPA"}]},
        "question_analysis": {"questions": [{"question": "What is accountant insurance?"}]},
    }


def brief():
    return {
        "brief_id": "brief_1",
        "report_id": "report_1",
        "decision_id": "decision_1",
        "strategy_id": "strategy_1",
        "lifecycle_stage": "content_brief_ready",
        "primary_keyword": "accountant insurance",
        "search_intent": "informational",
        "content_type": "guide",
        "outline": [{"section": "Coverage", "purpose": "explain coverage"}],
        "evidence_refs": ["e1"],
    }


def draft():
    return {
        "draft_id": "draft_1",
        "brief_id": "brief_1",
        "report_id": "report_1",
        "decision_id": "decision_1",
        "strategy_id": "strategy_1",
        "lifecycle_stage": "draft_ready",
        "title": "A Practical Guide to Accountant Insurance",
        "primary_keyword": "accountant insurance",
        "sections": [{
            "heading": "Coverage",
            "purpose": "coverage",
            "body": "Draft this section using evidence_refs and mark any claim that still requires editorial verification before publication.",
        }],
        "evidence_refs": ["e1"],
    }


def test_content_research_pipeline_reaches_wordpress_draft_contract():
    result = build_content_research_to_wordpress_draft(
        research_report=report(), content_brief=brief(), article_draft=draft()
    )
    assert result["seo_validation"]["outcome"] == "passed"
    assert result["editorial_review"]["outcome"] == "approved"
    assert result["publication"]["gate_status"] == "allowed"
    assert result["publisher"]["lifecycle_stage"] == "publisher_ready"
    assert result["wordpress_draft_delivery"]["lifecycle_stage"] == "wordpress_draft_ready"
    assert result["wordpress_draft_delivery"]["request_payload"]["status"] == "draft"


def test_content_research_pipeline_does_not_publish():
    result = build_content_research_to_wordpress_draft(
        research_report=report(), content_brief=brief(), article_draft=draft()
    )
    payload = result["wordpress_draft_delivery"]["request_payload"]
    assert payload["status"] == "draft"
    assert "publish" not in payload["status"]
