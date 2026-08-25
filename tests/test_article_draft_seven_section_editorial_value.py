from __future__ import annotations

from agents.research.article_draft import build_article_draft
from agents.research.article_draft_agent import _apply_faq_editorial_evidence


HEADINGS = [
    "Introduction",
    "What You Need to Know",
    "Coverage and Key Factors",
    "Costs and Pricing Factors",
    "How to Compare Options",
    "Frequently Asked Questions",
    "Sources and Editorial Methodology",
]


def _brief():
    return {
        "brief_id": "brief_7s",
        "report_id": "report_7s",
        "decision_id": "decision_7s",
        "strategy_id": "strategy_7s",
        "schema_version": "1.0",
        "lifecycle_stage": "content_brief_ready",
        "content_type": "guide",
        "primary_keyword": "consultant professional liability insurance",
        "outline": [{"heading": h, "purpose": f"Purpose for {h}"} for h in HEADINGS],
        "evidence_refs": ["core_1"],
        "editorial_constraints": ["verify factual claims"],
    }


def _core_records():
    return [{
        "evidence_id": "core_1",
        "domain": "research",
        "subject": {"type": "keyword", "id": "consultant professional liability insurance"},
        "claim": {"type": "observation", "attribute": "topic"},
        "value": {"type": "categorical", "data": "consultant professional liability insurance"},
    }]


def _page(section_index, evidence_id, text):
    return {
        "evidence_id": evidence_id,
        "section_index": section_index,
        "status": "ready",
        "text": text,
        "evidence_refs": [evidence_id],
        "source": {"type": "web_page", "url": f"https://example.com/{evidence_id}", "title": evidence_id},
        "provenance": {"artifact": "source-evidence.json", "method": "page-level-source-review-v1", "verification": "page_reviewed"},
        "domain": "editorial",
    }


def _artifact(section_index, evidence_id, text):
    item = _page(section_index, evidence_id, text)
    item["source"] = {"type": "artifact", "url": f"artifact://test/{evidence_id}", "title": evidence_id}
    item["provenance"] = {"artifact": "article-draft-pipeline", "method": "article-draft-evidence-contract-v1", "verification": "artifact_reviewed"}
    return item


def _source_evidence():
    return [
        _page(1, "intro_1", "The reviewed consultant guidance identifies professional liability as relevant to consultants providing services directly to customers."),
        _page(2, "know_1", "Reviewed guidance identifies errors, omissions, negligence, and inaccurate advice as consultant claim risks."),
        _page(3, "coverage_1", "Reviewed guidance describes professional liability protection for negligence and judgment errors arising from professional services."),
        _page(4, "cost_1", "Reviewed pricing guidance says consultant professional liability cost varies by business and coverage factors."),
        _page(5, "compare_1", "Reviewed guidance says consultants should compare limits, deductibles, exclusions, and policy terms."),
        _page(6, "faq_1", "Reviewed FAQ guidance explains how professional liability responds to client claims involving professional services."),
        _artifact(7, "method_1", "This draft uses section-scoped evidence contracts and preserves explicit evidence references and provenance."),
    ]


def _draft_with_faq_overlay():
    source = _source_evidence()
    draft = build_article_draft(content_brief=_brief(), evidence_records=_core_records(), source_evidence=source)
    _apply_faq_editorial_evidence(draft, source)
    return draft


def test_introduction_and_methodology_have_editorial_value():
    draft = _draft_with_faq_overlay()
    intro = draft["sections"][0]
    methodology = draft["sections"][6]

    assert intro["heading"] == "Introduction"
    assert intro["body"].strip()
    assert "consultant guidance" in intro["body"]
    assert intro["evidence_refs"] == ["intro_1"]
    assert intro["claims"]
    assert intro["claims"][0]["evidence_refs"] == ["intro_1"]

    assert methodology["heading"] == "Sources and Editorial Methodology"
    assert methodology["body"].strip()
    assert "section-scoped evidence contracts" in methodology["body"]
    assert methodology["evidence_refs"] == ["method_1"]
    assert methodology["claims"]
    assert methodology["claims"][0]["evidence_refs"] == ["method_1"]

    method_evidence = next(item for item in draft["editorial_evidence"] if item["evidence_id"] == "method_1")
    assert method_evidence["provenance"]["verification"] == "artifact_reviewed"


def test_all_seven_sections_are_linked_without_cross_section_leakage():
    draft = _draft_with_faq_overlay()

    assert [section["heading"] for section in draft["sections"]] == HEADINGS
    assert len(draft["sections"]) == 7

    top_refs = set(draft["evidence_refs"])
    editorial_by_id = {item["evidence_id"]: item for item in draft["editorial_evidence"]}
    claim_ids = []

    for index, section in enumerate(draft["sections"], 1):
        assert section["body"].strip()
        assert section["evidence_refs"]
        assert set(section["evidence_refs"]).issubset(top_refs)
        assert section["claims"]
        for claim in section["claims"]:
            claim_ids.append(claim["claim_id"])
            assert claim["grounding_status"] == "grounded"
            assert set(claim["evidence_refs"]).issubset(set(section["evidence_refs"]))

        if index in {1, 2, 3, 4, 5, 6}:
            for ref in section["evidence_refs"]:
                if ref in editorial_by_id:
                    assert editorial_by_id[ref]["provenance"]["verification"] == "page_reviewed"
        if index == 7:
            assert all(editorial_by_id[ref]["provenance"]["verification"] == "artifact_reviewed" for ref in section["evidence_refs"])

    assert draft["sections"][5]["evidence_refs"] == ["faq_1"]
    assert "Reviewed FAQ guidance" in draft["sections"][5]["body"]
    assert len(claim_ids) == len(set(claim_ids))
    assert all(not any(other["purpose"] in section["body"] for other in draft["sections"] if other is not section) for section in draft["sections"])


def test_editorial_evidence_is_deterministic():
    first = _draft_with_faq_overlay()
    second = _draft_with_faq_overlay()
    assert first == second
    assert first["draft_id"] == second["draft_id"]
