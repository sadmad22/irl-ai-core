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
        "outline": [{"heading": "Coverage", "purpose": "explain coverage"}],
        "evidence_refs": ["e1"],
    }


def draft():
    return {
        "draft_id": "draft_1",
        "brief_id": "brief_1",
        "report_id": "report_1",
        "decision_id": "decision_1",
        "strategy_id": "strategy_1",
        "schema_version": "1.0",
        "lifecycle_stage": "draft_ready",
        "title": "A Practical Guide to Accountant Insurance",
        "content_type": "guide",
        "primary_keyword": "accountant insurance",
        "sections": [{
            "heading": "Coverage",
            "purpose": "Explain the core coverage considerations.",
            "body": "Accountants may evaluate professional liability coverage based on the services they provide and their risk profile.",
        }],
        "evidence_refs": ["e1"],
        "editorial_constraints": ["verify factual claims"],
        "audit": {"method": "article_draft_agent", "version": "v1", "validation_status": "validated"},
    }


def test_content_research_pipeline_reaches_wordpress_draft_contract():
    result = build_content_research_to_wordpress_draft(
        research_report=report(), content_brief=brief(), article_draft=draft()
    )
    assert result["article_draft_quality"]["outcome"] == "passed"
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


def test_content_research_pipeline_stops_on_article_draft_quality_failure():
    value = draft()
    value["sections"][0]["body"] = "Draft this section to Address the requirement from the approved content strategy."

    result = build_content_research_to_wordpress_draft(
        research_report=report(), content_brief=brief(), article_draft=value
    )

    assert result["article_draft_quality"]["outcome"] == "needs_revision"
    assert result["article_draft_quality"]["checks"]["placeholders"] is False
    assert "seo_validation" not in result
    assert "editorial_review" not in result
    assert "publication" not in result
    assert "publisher" not in result
    assert "wordpress_draft_delivery" not in result
