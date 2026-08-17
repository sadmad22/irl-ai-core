import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agents.research.report import build_research_report

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "shared/schemas/research-report-assembly.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def test_builder_creates_canonical_pre_decision_report():
    report = build_research_report(
        report_id="rr_001",
        metadata={"id": "rr_001", "language": "en", "country": "US"},
        keyword={"keyword": "expat health insurance"},
        search_intent={"primary_intent": "informational"},
        search_metrics={"search_volume": 100},
        serp_analysis={"results": []},
        competitor_analysis={"competitors": []},
    )
    VALIDATOR.validate(report)
    assert report["report_id"] == "rr_001"
    assert report["lifecycle_stage"] == "research_complete"
    assert report["recommendation"] is None
    assert report["decision"] is None


def test_builder_preserves_evidence_references_without_duplicates():
    evidence = [
        {"evidence_id": "ev_1"},
        {"evidence_id": "ev_1"},
        {"evidence_id": "ev_2"},
    ]
    report = build_research_report(
        report_id="rr_001", metadata={}, keyword={"keyword": "kw"},
        search_intent={}, search_metrics={}, serp_analysis={}, competitor_analysis={},
        intent_evidence=evidence,
    )
    assert report["evidence_refs"]["intent"] == ["ev_1", "ev_2"]


def test_builder_keeps_domain_evidence_separate():
    report = build_research_report(
        report_id="rr_001", metadata={}, keyword={"keyword": "kw"},
        search_intent={}, search_metrics={}, serp_analysis={}, competitor_analysis={},
        entity_evidence=[{"evidence_id": "entity_1"}],
        question_evidence=[{"evidence_id": "question_1"}],
        business_evidence=[{"evidence_id": "business_1"}],
        authority_evidence=[{"evidence_id": "authority_1"}],
    )
    assert report["evidence_refs"] == {
        "intent": [],
        "entity": ["entity_1"],
        "question": ["question_1"],
        "business": ["business_1"],
        "authority": ["authority_1"],
    }


def test_builder_requires_report_id():
    try:
        build_research_report(
            report_id="", metadata={}, keyword={"keyword": "kw"},
            search_intent={}, search_metrics={}, serp_analysis={}, competitor_analysis={},
        )
    except ValueError as exc:
        assert "report_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_builder_requires_keyword():
    try:
        build_research_report(
            report_id="rr_001", metadata={}, keyword={}, search_intent={},
            search_metrics={}, serp_analysis={}, competitor_analysis={},
        )
    except ValueError as exc:
        assert "keyword.keyword" in str(exc)
    else:
        raise AssertionError("expected ValueError")
