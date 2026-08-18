from __future__ import annotations

import copy
import pytest

from agents.research.seo_strategy import build_seo_strategy


def brief():
    return {
        "brief_id":"brief_1","report_id":"report_1","decision_id":"decision_1","strategy_id":"strategy_1",
        "lifecycle_stage":"content_brief_ready","primary_keyword":"accountant insurance","search_intent":"commercial investigation",
        "evidence_refs":["e1","e2"],
        "outline":[{"heading":"Coverage","purpose":"coverage","body":""}],
        "internal_link_targets":["/professional-liability-insurance/"]
    }


def report():
    return {"report_id":"report_1","entity_analysis":{"entities":[{"entity":"CPA"},{"entity":"professional liability insurance"}]},"question_analysis":{"questions":[{"question":"What does accountant insurance cover?"}]}}


def test_builds_valid_strategy():
    result = build_seo_strategy(content_brief=brief(), research_report=report())
    assert result["lifecycle_stage"] == "seo_strategy_ready"
    assert result["primary_keyword"] == "accountant insurance"
    assert result["topical_entities"] == ["CPA","professional liability insurance"]


def test_preserves_lineage():
    result = build_seo_strategy(content_brief=brief(), research_report=report())
    assert result["brief_id"] == "brief_1"
    assert result["report_id"] == "report_1"
    assert result["decision_id"] == "decision_1"
    assert result["strategy_id"] == "strategy_1"
    assert result["evidence_refs"] == ["e1","e2"]


def test_is_deterministic():
    assert build_seo_strategy(content_brief=brief(), research_report=report()) == build_seo_strategy(content_brief=brief(), research_report=report())


def test_requires_brief_ready():
    bad = brief(); bad["lifecycle_stage"] = "draft_ready"
    with pytest.raises(ValueError): build_seo_strategy(content_brief=bad, research_report=report())


def test_rejects_report_mismatch():
    bad = report(); bad["report_id"] = "other"
    with pytest.raises(ValueError): build_seo_strategy(content_brief=brief(), research_report=bad)


def test_requires_evidence_refs():
    bad = brief(); bad["evidence_refs"] = []
    with pytest.raises(ValueError): build_seo_strategy(content_brief=bad, research_report=report())


def test_does_not_mutate_inputs():
    b = brief(); r = report(); bs = copy.deepcopy(b); rs = copy.deepcopy(r)
    build_seo_strategy(content_brief=b, research_report=r)
    assert b == bs and r == rs
