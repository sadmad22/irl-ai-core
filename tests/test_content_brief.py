import json
from pathlib import Path

import jsonschema
import pytest

from agents.research.content_brief import build_content_brief


def _report():
    return {
        "report_id": "rr_001",
        "lifecycle_stage": "research_complete",
        "search_intent": {"primary_intent": "commercial"},
    }


def _decision():
    return {
        "decision_id": "dec_001",
        "report_id": "rr_001",
        "lifecycle_stage": "decision_ready",
        "outcome": "approved",
    }


def _strategy():
    return {
        "strategy_id": "strat_001",
        "report_id": "rr_001",
        "decision_id": "dec_001",
        "lifecycle_stage": "content_strategy_ready",
        "content_type": "comparison",
        "primary_keyword": "expat health insurance",
        "audience": "Expat readers comparing insurance options",
        "business_goal": "Build qualified organic traffic and support informed insurance decisions.",
        "sections": ["Introduction", "Quick Comparison", "How to Choose"],
        "entities": ["Cigna Global", "Allianz Care"],
        "questions": ["How much does expat health insurance cost?"],
        "evidence_refs": ["ev_intent", "ev_business", "ev_authority"],
    }


def test_builds_valid_brief():
    brief = build_content_brief(research_report=_report(), decision=_decision(), content_strategy=_strategy())
    schema = json.loads(Path("shared/schemas/content-brief.schema.json").read_text())
    jsonschema.validate(brief, schema)
    assert brief["lifecycle_stage"] == "content_brief_ready"
    assert brief["decision_id"] == "dec_001"
    assert brief["strategy_id"] == "strat_001"


def test_preserves_evidence_lineage():
    brief = build_content_brief(research_report=_report(), decision=_decision(), content_strategy=_strategy())
    assert brief["evidence_refs"] == ["ev_intent", "ev_business", "ev_authority"]


def test_is_deterministic():
    first = build_content_brief(research_report=_report(), decision=_decision(), content_strategy=_strategy())
    second = build_content_brief(research_report=_report(), decision=_decision(), content_strategy=_strategy())
    assert first == second


def test_rejects_non_approved_decision():
    decision = _decision()
    decision["outcome"] = "deferred"
    with pytest.raises(ValueError, match="approved"):
        build_content_brief(research_report=_report(), decision=decision, content_strategy=_strategy())


def test_rejects_strategy_report_mismatch():
    strategy = _strategy()
    strategy["report_id"] = "rr_other"
    with pytest.raises(ValueError, match="report_id"):
        build_content_brief(research_report=_report(), decision=_decision(), content_strategy=strategy)


def test_rejects_strategy_decision_mismatch():
    strategy = _strategy()
    strategy["decision_id"] = "dec_other"
    with pytest.raises(ValueError, match="decision_id"):
        build_content_brief(research_report=_report(), decision=_decision(), content_strategy=strategy)


def test_does_not_generate_article_prose():
    brief = build_content_brief(research_report=_report(), decision=_decision(), content_strategy=_strategy())
    assert "article" not in brief
    assert "draft" not in brief
    assert all("purpose" in item for item in brief["outline"])
