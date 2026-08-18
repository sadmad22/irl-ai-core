from __future__ import annotations
import copy
import pytest
from agents.research.seo_strategy_agent import run_seo_strategy_agent

def brief():
    return {
        "brief_id":"brief_1","report_id":"report_1","decision_id":"decision_1","strategy_id":"strategy_1",
        "lifecycle_stage":"content_brief_ready","primary_keyword":"accountant insurance","search_intent":"commercial investigation",
        "evidence_refs":["e1","e2"],"outline":[{"heading":"Coverage","purpose":"coverage","body":""}],
        "internal_link_targets":["/professional-liability-insurance/"]}

def report():
    return {"report_id":"report_1","entity_analysis":{"entities":[{"entity":"CPA"}]},"question_analysis":{"questions":[{"question":"What does accountant insurance cover?"}]}}

def test_agent_builds_ready_strategy_end_to_end():
    result = run_seo_strategy_agent(content_brief=brief(), research_report=report())
    assert result["lifecycle_stage"] == "seo_strategy_ready"
    assert result["brief_id"] == "brief_1"
    assert result["report_id"] == "report_1"
    assert result["evidence_refs"] == ["e1", "e2"]

def test_agent_is_deterministic_and_preserves_inputs():
    b, r = brief(), report(); bs, rs = copy.deepcopy(b), copy.deepcopy(r)
    first = run_seo_strategy_agent(content_brief=b, research_report=r)
    second = run_seo_strategy_agent(content_brief=b, research_report=r)
    assert first == second
    assert b == bs and r == rs

def test_agent_rejects_non_ready_brief():
    b = brief(); b["lifecycle_stage"] = "draft_ready"
    with pytest.raises(ValueError):
        run_seo_strategy_agent(content_brief=b, research_report=report())
