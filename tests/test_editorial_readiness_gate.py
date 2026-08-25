from __future__ import annotations

from copy import deepcopy

from agents.research.editorial_readiness_gate import evaluate_editorial_readiness


def _draft():
    evidence = []
    sections = []
    headings = [
        "Introduction",
        "What You Need to Know",
        "Coverage and Key Factors",
        "Costs and Pricing Factors",
        "How to Compare Options",
        "Frequently Asked Questions",
        "Sources and Editorial Methodology",
    ]
    for index, heading in enumerate(headings, 1):
        evidence_id = f"page_{index}"
        verification = "artifact_reviewed" if index == 7 else "page_reviewed"
        evidence.append({
            "evidence_id": evidence_id,
            "section_index": index,
            "status": "ready",
            "text": f"Grounded evidence for {heading}.",
            "source": {
                "type": "artifact" if index == 7 else "web_page",
                "url": f"https://example.com/{index}",
                "title": f"Reviewed source for {heading}",
                "domain": "example.com",
            },
            "provenance": {
                "artifact": "article-draft-pipeline" if index == 7 else "source-evidence.json",
                "method": "article-draft-evidence-contract-v1" if index == 7 else "page-level-source-review-v1",
                "verification": verification,
            },
        })
        sections.append({
            "heading": heading,
            "purpose": f"Purpose {index}",
            "body": f"Grounded evidence for {heading}.",
            "evidence_refs": [evidence_id],
            "claims": [{
                "claim_id": f"claim_{index}_1_test",
                "text": f"Grounded evidence for {heading}.",
                "evidence_refs": [evidence_id],
                "grounding_status": "grounded",
            }],
        })
    return {
        "draft_id": "draft_gate",
        "brief_id": "brief_gate",
        "report_id": "report_gate",
        "decision_id": "decision_gate",
        "strategy_id": "strategy_gate",
        "schema_version": "1.0",
        "lifecycle_stage": "draft_ready",
        "title": "Consultant Professional Liability Insurance",
        "content_type": "guide",
        "primary_keyword": "consultant professional liability insurance",
        "sections": sections,
        "evidence_refs": [f"page_{i}" for i in range(1, 8)],
        "editorial_evidence": evidence,
        "section_evidence_contracts": [
            {"section_index": i, "heading": headings[i - 1], "status": "ready", "evidence_refs": [f"page_{i}"]}
            for i in range(1, 8)
        ],
        "editorial_constraints": [],
        "audit": {
            "method": "content_brief_to_section_and_claim_grounded_article_draft",
            "version": "v9",
            "validation_status": "pending",
        },
    }


def test_valid_draft_reaches_wordpress_draft_ready_without_publish_permission():
    result = evaluate_editorial_readiness(article_draft=_draft())
    assert result["outcome"] == "passed"
    assert result["target_lifecycle_stage"] == "wordpress_draft_ready"
    assert result["publish_allowed"] is False
    assert result["wordpress_write_allowed"] is False


def test_missing_section_evidence_fails_safe_to_needs_revision():
    draft = _draft()
    draft["sections"][3]["evidence_refs"] = []
    result = evaluate_editorial_readiness(article_draft=draft)
    assert result["outcome"] == "needs_revision"
    assert result["target_lifecycle_stage"] == "needs_revision"
    assert result["publish_allowed"] is False
    assert result["wordpress_write_allowed"] is False
    assert result["findings"]


def test_page_reviewed_requirement_cannot_be_bypassed():
    draft = _draft()
    draft["editorial_evidence"][0]["provenance"]["verification"] = "snippet_only"
    result = evaluate_editorial_readiness(article_draft=draft)
    assert result["outcome"] == "needs_revision"
    assert result["target_lifecycle_stage"] == "needs_revision"


def test_gate_does_not_mutate_draft():
    draft = _draft()
    before = deepcopy(draft)
    evaluate_editorial_readiness(article_draft=draft)
    assert draft == before


def test_gate_is_deterministic():
    first = evaluate_editorial_readiness(article_draft=_draft())
    second = evaluate_editorial_readiness(article_draft=_draft())
    assert first == second
