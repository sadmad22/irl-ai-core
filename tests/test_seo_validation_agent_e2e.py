from __future__ import annotations
import copy
import pytest
from agents.research.seo_validation_agent import run_seo_validation_agent

def strategy():
    return {"seo_strategy_id":"seo_1","brief_id":"brief_1","report_id":"report_1","decision_id":"decision_1","strategy_id":"strategy_1","lifecycle_stage":"seo_strategy_ready","primary_keyword":"accountant insurance","search_intent":"commercial investigation","title_requirements":["primary keyword"],"meta_description_requirements":["accurate summary"],"heading_requirements":["Coverage"],"topical_entities":["CPA"],"questions_to_answer":[],"internal_link_targets":[],"schema_requirements":[],"image_alt_requirements":[],"evidence_refs":["e1","e2"]}

def draft():
    return {"draft_id":"draft_1","brief_id":"brief_1","report_id":"report_1","decision_id":"decision_1","strategy_id":"strategy_1","lifecycle_stage":"draft_ready","title":"Accountant Insurance Guide","primary_keyword":"accountant insurance","evidence_refs":["e1","e2"],"sections":[{"heading":"Coverage","purpose":"coverage","body":"evidence"}]}

def test_agent_builds_validation_end_to_end():
    result = run_seo_validation_agent(article_draft=draft(), seo_strategy=strategy())
    assert result["lifecycle_stage"] == "seo_validation_ready"
    assert result["outcome"] == "passed"
    assert result["draft_id"] == "draft_1"
    assert result["seo_strategy_id"] == "seo_1"

def test_agent_is_deterministic_and_preserves_inputs():
    d, s = draft(), strategy(); ds, ss = copy.deepcopy(d), copy.deepcopy(s)
    first = run_seo_validation_agent(article_draft=d, seo_strategy=s)
    second = run_seo_validation_agent(article_draft=d, seo_strategy=s)
    assert first == second
    assert d == ds and s == ss

def test_agent_rejects_invalid_draft_lifecycle():
    d = draft(); d["lifecycle_stage"] = "draft_pending"
    with pytest.raises(ValueError):
        run_seo_validation_agent(article_draft=d, seo_strategy=strategy())
