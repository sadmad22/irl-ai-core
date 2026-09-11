import json

import pytest

from agents.research.article_draft import build_article_draft


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
    return [
        {
            "evidence_id": "ev_1",
            "domain": "entity",
            "subject": {"type": "keyword", "id": "expat health insurance"},
            "claim": {"type": "observation", "attribute": "coverage"},
            "value": {"type": "categorical", "data": "international"},
        },
        {
            "evidence_id": "ev_2",
            "domain": "serp",
            "subject": {"type": "keyword", "id": "expat health insurance"},
            "claim": {"type": "comparison_signal", "attribute": "provider"},
            "value": {"type": "categorical", "data": "commercial"},
        },
    ]


def _build():
    return build_article_draft(
        content_brief=_brief(),
        evidence_records=_evidence_records(),
        llm_provider=FakeWriter(),
    )


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


def test_article_draft_is_deterministic():
    first = _build()
    second = _build()
    assert first == second
    assert first["draft_id"] == second["draft_id"]


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
