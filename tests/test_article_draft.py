import json

import pytest

from agents.research.article_draft import build_article_draft


def _brief():
    return {
        "brief_id": "brief_001",
        "report_id": "rr_001",
        "decision_id": "dec_001",
        "strategy_id": "strat_001",
        "schema_version": "1.0",
        "lifecycle_stage": "content_brief_ready",
        "content_type": "guide",
        "primary_keyword": "best expat health insurance",
        "search_intent": "commercial",
        "audience": "expats",
        "objective": "help readers compare options",
        "title_direction": "guide framing",
        "outline": [
            {"heading": "What Is Expat Health Insurance?", "purpose": "define the topic"},
            {"heading": "How to Compare Plans", "purpose": "explain selection criteria"},
        ],
        "required_entities": ["Cigna Global"],
        "required_questions": ["What does it cost?"],
        "evidence_refs": ["ev_1", "ev_2"],
        "editorial_constraints": ["verify factual claims"],
        "audit": {"method": "test", "version": "v1", "validation_status": "pending"},
    }


def test_article_draft_contract_shape():
    draft = build_article_draft(content_brief=_brief())
    assert draft["lifecycle_stage"] == "draft_ready"
    assert draft["brief_id"] == "brief_001"
    assert draft["report_id"] == "rr_001"
    assert draft["decision_id"] == "dec_001"
    assert draft["strategy_id"] == "strat_001"
    assert draft["evidence_refs"] == ["ev_1", "ev_2"]
    assert len(draft["sections"]) == 2


def test_article_draft_is_deterministic():
    first = build_article_draft(content_brief=_brief())
    second = build_article_draft(content_brief=_brief())
    assert first == second
    assert first["draft_id"] == second["draft_id"]


def test_article_draft_preserves_lineage():
    draft = build_article_draft(content_brief=_brief())
    assert {draft[k] for k in ("brief_id", "report_id", "decision_id", "strategy_id")} == {
        "brief_001", "rr_001", "dec_001", "strat_001"
    }


def test_article_draft_requires_ready_brief():
    brief = _brief()
    brief["lifecycle_stage"] = "content_strategy_ready"
    with pytest.raises(ValueError, match="content_brief_ready"):
        build_article_draft(content_brief=brief)


def test_article_draft_requires_evidence_refs():
    brief = _brief()
    brief["evidence_refs"] = []
    with pytest.raises(ValueError, match="evidence_refs"):
        build_article_draft(content_brief=brief)


def test_article_draft_does_not_change_brief():
    brief = _brief()
    snapshot = json.loads(json.dumps(brief))
    build_article_draft(content_brief=brief)
    assert brief == snapshot


def test_article_draft_is_not_a_decision_engine():
    draft = build_article_draft(content_brief=_brief())
    assert "decision" not in draft
    assert "recommendation" not in draft
