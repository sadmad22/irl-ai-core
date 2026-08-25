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
        "brief_id": "brief_article_level",
        "report_id": "report_article_level",
        "decision_id": "decision_article_level",
        "strategy_id": "strategy_article_level",
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
        _page(6, "editorial_page_hartford_faq_workflow_20260825", "Reviewed FAQ guidance explains how professional liability responds to client claims involving professional services."),
        _page(6, "editorial_page_hartford_faq_coverage_20260825", "Reviewed FAQ guidance explains covered errors, omissions, negligence, and defense costs."),
        _page(6, "editorial_page_hartford_faq_need_20260825", "Reviewed FAQ guidance identifies businesses providing services or advice as candidates for professional liability coverage."),
        _page(6, "editorial_page_insureon_faq_consultants_20260825", "Reviewed FAQ guidance identifies consultants among businesses that should consider professional liability insurance."),
        _artifact(7, "method_1", "This draft uses section-scoped evidence contracts and preserves explicit evidence references and provenance."),
    ]


def _draft():
    source = _source_evidence()
    draft = build_article_draft(content_brief=_brief(), evidence_records=_core_records(), source_evidence=source)
    _apply_faq_editorial_evidence(draft, source)
    return draft


def test_article_level_has_all_sections_and_no_empty_editorial_sections():
    draft = _draft()
    assert [s["heading"] for s in draft["sections"]] == HEADINGS
    assert all(s["body"].strip() for s in draft["sections"])
    assert all(s["claims"] for s in draft["sections"])


def test_article_level_lineage_is_closed():
    draft = _draft()
    top = set(draft["evidence_refs"])
    editorial = {x["evidence_id"]: x for x in draft["editorial_evidence"]}
    claim_ids = []
    for index, section in enumerate(draft["sections"], 1):
        refs = set(section["evidence_refs"])
        assert refs
        assert refs <= top
        for claim in section["claims"]:
            claim_ids.append(claim["claim_id"])
            assert claim["grounding_status"] == "grounded"
            assert set(claim["evidence_refs"]) <= refs
            assert set(claim["evidence_refs"]) <= set(editorial)
        if index <= 6:
            assert all(editorial[ref]["provenance"]["verification"] == "page_reviewed" for ref in refs if ref in editorial)
        if index == 7:
            assert all(editorial[ref]["provenance"]["verification"] == "artifact_reviewed" for ref in refs)
    assert len(claim_ids) == len(set(claim_ids))


def test_article_level_sections_have_distinct_editorial_roles():
    draft = _draft()
    bodies = {s["heading"]: s["body"] for s in draft["sections"]}
    assert bodies["Introduction"] != bodies["What You Need to Know"]
    assert bodies["Coverage and Key Factors"] != bodies["Costs and Pricing Factors"]
    assert bodies["Costs and Pricing Factors"] != bodies["How to Compare Options"]
    assert bodies["Frequently Asked Questions"] != bodies["How to Compare Options"]
    assert "section-scoped evidence contracts" in bodies["Sources and Editorial Methodology"]


def test_article_level_draft_is_deterministic():
    assert _draft() == _draft()
