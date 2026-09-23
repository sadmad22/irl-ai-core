from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research import article_draft
from agents.research.section_evidence_readiness import evaluate_section_readiness, require_ready_sections


def _outline():
    return [{"heading": "Introduction", "purpose": "Explain the topic and search intent."}]


def _record(
    *,
    evidence_id: str,
    claim_type: str,
    attribute: str,
    source_type: str = "official",
    source_id: str | None = None,
    domain: str = "topic",
    value: object = "Expat health insurance is coverage for people living abroad.",
    evidence_type: str = "observation",
    derived_from: list[str] | None = None,
):
    return {
        "evidence_id": evidence_id,
        "report_id": "rr_test",
        "schema_version": "1.0",
        "type": evidence_type,
        "domain": domain,
        "subject": {"type": "keyword", "id": "expat health insurance"},
        "claim": {"type": claim_type, "attribute": attribute},
        "value": {"type": "categorical", "data": value},
        "source": {
            "type": source_type,
            "source_id": source_id or f"source:{evidence_id}",
            "provider": "test",
            "retrieved_at": "2026-09-23T12:00:00Z",
        },
        "provenance": {
            "analyzer": "test",
            "analyzer_version": "1.0",
            "method": "deterministic_test",
        },
        "confidence": 1.0,
        "relation": "supports",
        "derived_from": derived_from if derived_from is not None else [],
        "captured_at": "2026-09-23T12:00:00Z",
        "status": "active",
    }


def _intro_evidence():
    return [
        _record(
            evidence_id="ev_definition",
            claim_type="topic_definition",
            attribute="definition",
            source_id="source:official-topic",
            value="Expat health insurance is international health coverage for people living abroad.",
        ),
        _record(
            evidence_id="ev_intent",
            claim_type="query_intent",
            attribute="primary_intent",
            source_type="query",
            source_id="source:query",
            domain="intent",
            value="Informational",
        ),
    ]


def test_readiness_result_matches_schema():
    result = evaluate_section_readiness(
        outline=_outline(),
        evidence_refs=["ev_definition", "ev_intent"],
        evidence_records=_intro_evidence(),
    )
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "shared"
            / "schemas"
            / "section-evidence-readiness.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(result[0])


def test_ready_when_required_claims_have_eligible_support():
    result = evaluate_section_readiness(
        outline=_outline(),
        evidence_refs=["ev_definition", "ev_intent"],
        evidence_records=_intro_evidence(),
    )

    assert len(result) == 1
    assert result[0]["readiness"] == "READY"
    assert result[0]["missing_required_claims"] == []
    assert {
        (item["claim_type"], item["attribute"])
        for item in result[0]["supported_required_claims"]
    } == {
        ("topic_definition", "definition"),
        ("query_intent", "primary_intent"),
    }


def test_unknown_section_is_blocked_instead_of_defaulting_to_introduction():
    result = evaluate_section_readiness(
        outline=[{"heading": "Unmapped Research Section", "purpose": "unknown"}],
        evidence_refs=["ev_definition", "ev_intent"],
        evidence_records=_intro_evidence(),
    )

    assert result[0]["readiness"] == "BLOCKED"
    assert result[0]["section_key"] == ""
    assert result[0]["reason_codes"] == ["context_missing"]



def test_insufficient_when_required_claim_is_uncovered():
    result = evaluate_section_readiness(
        outline=_outline(),
        evidence_refs=["ev_definition"],
        evidence_records=_intro_evidence(),
    )

    item = result[0]
    assert item["readiness"] == "INSUFFICIENT"
    assert {"claim_type": "query_intent", "attribute": "primary_intent"} in item["missing_required_claims"]
    assert "required_claim_missing" in item["reason_codes"]


def test_insufficient_when_section_has_no_eligible_evidence():
    result = evaluate_section_readiness(
        outline=_outline(),
        evidence_refs=["ev_unrelated"],
        evidence_records=[
            _record(
                evidence_id="ev_unrelated",
                claim_type="business_value",
                attribute="commercial_value",
                domain="business",
                source_type="secondary",
            )
        ],
    )

    item = result[0]
    assert item["readiness"] == "INSUFFICIENT"
    assert item["eligible_evidence_refs"] == []
    assert "no_eligible_supporting_evidence" in item["reason_codes"]


def test_blocked_when_eligible_evidence_violates_canonical_contract():
    bad = _record(
        evidence_id="ev_bad",
        claim_type="topic_definition",
        attribute="definition",
    )
    del bad["provenance"]["analyzer_version"]

    result = evaluate_section_readiness(
        outline=_outline(),
        evidence_refs=["ev_bad"],
        evidence_records=[bad],
    )

    assert result[0]["readiness"] == "BLOCKED"
    assert result[0]["dimension_results"]["integrity"] == "FAIL"
    assert "evidence_contract_invalid" in result[0]["reason_codes"]


def test_blocked_when_derived_evidence_has_no_lineage():
    bad = _record(
        evidence_id="ev_derived",
        claim_type="topic_definition",
        attribute="definition",
        evidence_type="derived",
        derived_from=[],
    )

    result = evaluate_section_readiness(
        outline=_outline(),
        evidence_refs=["ev_derived"],
        evidence_records=[bad],
    )

    assert result[0]["readiness"] == "BLOCKED"
    assert result[0]["dimension_results"]["lineage"] == "FAIL"
    assert "lineage_invalid" in result[0]["reason_codes"]


def test_weak_discovery_source_does_not_satisfy_substantive_claim():
    records = [
        _record(
            evidence_id="ev_definition",
            claim_type="topic_definition",
            attribute="definition",
            source_type="community",
            source_id="source:forum",
        ),
        _record(
            evidence_id="ev_intent",
            claim_type="query_intent",
            attribute="primary_intent",
            source_type="query",
            source_id="source:query",
            domain="intent",
            value="Informational",
        ),
    ]

    result = evaluate_section_readiness(
        outline=_outline(),
        evidence_refs=["ev_definition", "ev_intent"],
        evidence_records=records,
    )

    assert result[0]["readiness"] == "INSUFFICIENT"
    assert result[0]["dimension_results"]["authority"] == "FAIL"
    assert "authority_insufficient" in result[0]["reason_codes"]


def test_duplicate_source_origin_is_not_counted_as_diversity():
    outline = [{"heading": "How to Compare Options", "purpose": "Explain factual option differences."}]
    records = [
        _record(
            evidence_id="ev_criterion",
            claim_type="comparison_fact",
            attribute="criterion",
            source_id="source:same",
            domain="comparison",
            value="Coverage and cost are comparison criteria.",
        ),
        _record(
            evidence_id="ev_coverage_difference",
            claim_type="option_attribute",
            attribute="coverage_difference",
            source_id="source:same",
            domain="comparison",
            value="Options can differ in the coverage they provide.",
        ),
        _record(
            evidence_id="ev_cost_difference",
            claim_type="option_attribute",
            attribute="cost_difference",
            source_id="source:same",
            domain="comparison",
            value="Options can differ in cost based on their terms.",
        ),
    ]

    result = evaluate_section_readiness(
        outline=outline,
        evidence_refs=["ev_criterion", "ev_coverage_difference", "ev_cost_difference"],
        evidence_records=records,
    )

    assert result[0]["dimension_results"]["coverage"] == "PASS"
    assert result[0]["dimension_results"]["diversity"] == "FAIL"
    assert "diversity_insufficient" in result[0]["reason_codes"]
    assert result[0]["readiness"] == "INSUFFICIENT"



def test_gate_prevents_writer_from_receiving_unready_section(monkeypatch):
    called = False

    def fake_writer(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("Writer must not be called when readiness is not satisfied")

    monkeypatch.setattr(article_draft, "write_article_draft", fake_writer)
    brief = {
        "brief_id": "brief_test",
        "report_id": "rr_test",
        "decision_id": "dec_test",
        "strategy_id": "strat_test",
        "lifecycle_stage": "content_brief_ready",
        "content_type": "guide",
        "primary_keyword": "expat health insurance",
        "outline": _outline(),
        "evidence_refs": ["ev_definition"],
        "editorial_constraints": [],
    }

    with pytest.raises(ValueError, match="Quality Gate blocked Article Writer"):
        article_draft.build_article_draft(
            content_brief=brief,
            evidence_records=_intro_evidence(),
            llm_provider=object(),
        )

    assert called is False


def test_ready_gate_allows_writer_path_to_continue():
    calls = []

    class FakeWriter:
        def write(self, *, sections, editorial_rules):
            calls.append(sections)
            return {
                "sections": [
                    {"section_index": item["section_index"], "body": "Expat health insurance provides an international health coverage context. Informational readers can evaluate the topic."}
                    for item in sections
                ],
                "tables": [],
                "images": [
                    {
                        "image_id": "img_1",
                        "section_index": 0,
                        "placement": "after introduction",
                        "prompt": "Editorial insurance illustration.",
                        "alt_text": "Insurance illustration",
                        "evidence_refs": sections[0]["evidence_refs"],
                    }
                ],
            }

    brief = {
        "brief_id": "brief_ready",
        "report_id": "rr_test",
        "decision_id": "dec_test",
        "strategy_id": "strat_test",
        "lifecycle_stage": "content_brief_ready",
        "content_type": "guide",
        "primary_keyword": "expat health insurance",
        "outline": _outline(),
        "evidence_refs": ["ev_definition", "ev_intent"],
        "editorial_constraints": [],
    }

    draft = article_draft.build_article_draft(
        content_brief=brief,
        evidence_records=_intro_evidence(),
        llm_provider=FakeWriter(),
    )

    assert calls
    assert draft["lifecycle_stage"] == "draft_ready"


def test_readiness_result_is_deterministic():
    kwargs = {
        "outline": _outline(),
        "evidence_refs": ["ev_definition", "ev_intent"],
        "evidence_records": _intro_evidence(),
    }
    assert evaluate_section_readiness(**kwargs) == evaluate_section_readiness(**kwargs)


def test_require_ready_sections_returns_results_for_ready_input():
    result = require_ready_sections(
        outline=_outline(),
        evidence_refs=["ev_definition", "ev_intent"],
        evidence_records=_intro_evidence(),
    )
    assert result[0]["readiness"] == "READY"
