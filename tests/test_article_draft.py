import json

import pytest

from agents.research.article_draft import _draft_id, build_article_draft


class FakeWriter:
    def write(self, *, sections, editorial_rules):
        return {
            "sections": [
                {"section_index": 0, "body": "Expat health insurance can help cover eligible healthcare needs across countries, depending on the plan and network."},
                {"section_index": 1, "body": "When comparing plans, readers should examine the coverage offered and the type of provider or network available."},
            ],
            "tables": [],
            "images": [
                {
                    "image_id": "img_1",
                    "section_index": 0,
                    "placement": "after introduction",
                    "prompt": "Editorial illustration of an expat reviewing international health insurance coverage, clean research-platform style, no text.",
                    "alt_text": "Expat reviewing international health insurance coverage",
                    "evidence_refs": ["ev_1"],
                }
            ],
        }


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


def _evidence_records():
    base = {
        "report_id": "rr_001",
        "schema_version": "1.0",
        "type": "observation",
        "subject": {"type": "keyword", "id": "best expat health insurance"},
        "source": {
            "type": "official",
            "source_id": "source:test",
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
        "derived_from": [],
        "captured_at": "2026-09-23T12:00:00Z",
        "status": "active",
    }
    return [
        {
            **base,
            "evidence_id": "ev_1",
            "domain": "topic",
            "claim": {"type": "topic_definition", "attribute": "definition"},
            "value": {"type": "text", "data": "Expat health insurance provides international health coverage for people living abroad."},
        },
        {
            **base,
            "evidence_id": "ev_2",
            "domain": "intent",
            "claim": {"type": "query_intent", "attribute": "primary_intent"},
            "value": {"type": "categorical", "data": "Informational"},
            "source": {
                "type": "query",
                "source_id": "source:query",
                "provider": "test",
                "retrieved_at": "2026-09-23T12:00:00Z",
            },
        },
        {
            **base,
            "evidence_id": "ev_3",
            "domain": "comparison",
            "claim": {"type": "comparison_fact", "attribute": "criterion"},
            "value": {"type": "text", "data": "Compare coverage, cost, and network terms when reviewing plans."},
        },
        {
            **base,
            "evidence_id": "ev_4",
            "domain": "comparison",
            "claim": {"type": "option_attribute", "attribute": "coverage_difference"},
            "value": {"type": "text", "data": "Plans can differ in the coverage they provide."},
            "source": {**base["source"], "source_id": "source:coverage"},
        },
        {
            **base,
            "evidence_id": "ev_5",
            "domain": "comparison",
            "claim": {"type": "option_attribute", "attribute": "cost_difference"},
            "value": {"type": "text", "data": "Plans can differ in cost based on their terms."},
            "source": {**base["source"], "source_id": "source:cost"},
        },
    ]


def _build():
    return build_article_draft(
        content_brief=_brief(),
        evidence_records=_evidence_records(),
        llm_provider=FakeWriter(),
    )


def test_writer_receives_heading_as_context_without_generating_it():
    captured = {}

    class CapturingWriter(FakeWriter):
        def write(self, *, sections, editorial_rules):
            captured["sections"] = sections
            captured["rules"] = editorial_rules
            return super().write(sections=sections, editorial_rules=editorial_rules)

    build_article_draft(
        content_brief=_brief(),
        evidence_records=_evidence_records(),
        llm_provider=CapturingWriter(),
    )

    assert [section["heading"] for section in captured["sections"]] == [
        "What Is Expat Health Insurance?",
        "How to Compare Plans",
    ]
    assert all(section["purpose"] for section in captured["sections"])
    assert captured["rules"]["evidence_constrained_prose"] is True
    assert captured["rules"]["factual_claims_must_be_supported_by_assigned_evidence"] is True
    assert captured["rules"]["do_not_use_unassigned_evidence"] is True
    assert captured["rules"]["omit_or_reframe_unsupported_factual_statements"] is True
    assert captured["rules"]["avoid_broad_unsourced_generalizations"] is True
    assert captured["rules"]["heading_is_external"] is True
    assert "The section heading is supplied externally and must not be generated." in captured["rules"]["evidence_constrained_writing_instructions"]
    assert "assigned to that section" in captured["rules"]["evidence_constrained_writing_instructions"]
    assert "must not be generated" in captured["rules"]["evidence_constrained_writing_instructions"]


def test_article_draft_contract_shape():
    draft = _build()
    assert draft["lifecycle_stage"] == "draft_ready"
    assert draft["schema_version"] == "1.1"
    assert draft["brief_id"] == "brief_001"
    assert draft["report_id"] == "rr_001"
    assert draft["decision_id"] == "dec_001"
    assert draft["strategy_id"] == "strat_001"
    assert draft["evidence_refs"] == ["ev_1", "ev_2"]
    assert len(draft["sections"]) == 2
    assert len(draft["images"]) == 1


def test_article_draft_persists_ready_section_evidence_contracts():
    draft = _build()
    assert draft["section_evidence_contracts"] == [
        {
            "section_index": 1,
            "heading": "What Is Expat Health Insurance?",
            "status": "ready",
            "evidence_refs": ["ev_1", "ev_2"],
        },
        {
            "section_index": 2,
            "heading": "How to Compare Plans",
            "status": "ready",
            "evidence_refs": ["ev_3", "ev_4", "ev_5"],
        },
    ]



def test_article_draft_is_deterministic():
    first = _build()
    second = _build()
    assert first == second
    assert first["draft_id"] == second["draft_id"]


def test_draft_id_preserves_canonical_json_serialization():
    payload = {
        "title": "x",
        "content_type": "guide",
        "primary_keyword": "k",
        "sections": [],
        "tables": [],
        "images": [],
        "evidence_refs": ["ev_1"],
        "editorial_constraints": [],
    }
    assert _draft_id({"brief_id": "brief_001"}, payload) == "draft_0a2f1e6a421504a9"


def test_article_draft_preserves_lineage():
    draft = _build()
    assert {draft[k] for k in ("brief_id", "report_id", "decision_id", "strategy_id")} == {
        "brief_001", "rr_001", "dec_001", "strat_001"
    }


def test_article_draft_requires_writer_provider():
    with pytest.raises(ValueError, match="explicitly injected LLM provider"):
        build_article_draft(content_brief=_brief(), evidence_records=_evidence_records(), llm_provider=None)


def test_article_draft_requires_ready_brief():
    brief = _brief()
    brief["lifecycle_stage"] = "content_strategy_ready"
    with pytest.raises(ValueError, match="content_brief_ready"):
        build_article_draft(content_brief=brief, llm_provider=FakeWriter())


def test_article_draft_requires_evidence_refs():
    brief = _brief()
    brief["evidence_refs"] = []
    with pytest.raises(ValueError, match="evidence_refs"):
        build_article_draft(content_brief=brief, llm_provider=FakeWriter())


def test_article_draft_does_not_change_brief():
    brief = _brief()
    snapshot = json.loads(json.dumps(brief))
    build_article_draft(content_brief=brief, evidence_records=_evidence_records(), llm_provider=FakeWriter())
    assert brief == snapshot


def test_article_draft_is_not_a_decision_engine():
    draft = _build()
    assert "decision" not in draft
    assert "recommendation" not in draft


def test_writer_output_does_not_leak_research_metadata():
    draft = _build()
    for section in draft["sections"]:
        assert "The research evidence records" not in section["body"]
        assert "evidence_id" not in section["body"]
        assert section["purpose"] not in section["body"]
        assert section["body"].strip()


def test_writer_output_contains_structured_image_spec():
    image = _build()["images"][0]
    assert image["prompt"]
    assert image["alt_text"]
    assert image["placement"]
    assert image["evidence_refs"]
    assert "url" not in image
    assert "src" not in image


def test_comparison_draft_requires_table():
    brief = _brief()
    brief["content_type"] = "comparison"
    with pytest.raises(ValueError, match="structured table"):
        build_article_draft(content_brief=brief, evidence_records=_evidence_records(), llm_provider=FakeWriter())


def test_writer_rejects_internal_metadata_leakage():
    class LeakyWriter(FakeWriter):
        def write(self, *, sections, editorial_rules):
            result = super().write(sections=sections, editorial_rules=editorial_rules)
            result["sections"][0]["body"] = "The research evidence records coverage for evidence_id ev_1."
            return result

    with pytest.raises(ValueError, match="internal research metadata"):
        build_article_draft(content_brief=_brief(), evidence_records=_evidence_records(), llm_provider=LeakyWriter())


def test_claim_ids_are_globally_unique_and_encode_section_identity():
    draft = _build()
    claims = [claim for section in draft["sections"] for claim in section["claims"]]
    claim_ids = [claim["claim_id"] for claim in claims]

    assert len(claim_ids) == len(set(claim_ids))
    assert all(claim_id.startswith(f"claim_{index}_") for index, section in enumerate(draft["sections"], 1) for claim_id in [section["claims"][0]["claim_id"]])
