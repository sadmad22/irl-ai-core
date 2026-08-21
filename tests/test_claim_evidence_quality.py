from agents.research.article_draft_quality import validate_article_draft_quality


def _draft():
    return {
        "draft_id": "draft_1", "brief_id": "brief_1", "report_id": "report_1", "decision_id": "decision_1", "strategy_id": "strategy_1",
        "schema_version": "1.0", "lifecycle_stage": "draft_ready", "title": "Guide", "content_type": "guide", "primary_keyword": "insurance",
        "sections": [{
            "heading": "Coverage", "purpose": "Explain coverage.", "body": "Coverage can vary by plan.",
            "evidence_refs": ["e1"],
            "claims": [{"claim_id": "claim_1_1_abc", "text": "Coverage can vary by plan.", "evidence_refs": ["e1"], "grounding_status": "grounded"}],
        }],
        "evidence_refs": ["e1"], "editorial_constraints": [],
        "audit": {"method": "test", "version": "v2", "validation_status": "pending"},
    }


def test_valid_claim_gate_passes():
    result = validate_article_draft_quality(article_draft=_draft())
    assert result["checks"]["claim_evidence_grounding"] is True
    assert result["outcome"] == "passed"


def test_duplicate_claim_id_across_sections_fails():
    value = _draft()
    section = dict(value["sections"][0])
    section["heading"] = "Costs"
    section["claims"] = [dict(section["claims"][0])]
    value["sections"].append(section)
    result = validate_article_draft_quality(article_draft=value)
    assert result["checks"]["claim_evidence_grounding"] is False
    assert result["outcome"] == "needs_revision"


def test_claim_id_must_match_section_identity():
    value = _draft()
    value["sections"][0]["claims"][0]["claim_id"] = "claim_2_1_abc"
    result = validate_article_draft_quality(article_draft=value)
    assert result["checks"]["claim_evidence_grounding"] is False


def test_blocked_claim_must_not_carry_evidence():
    value = _draft()
    value["sections"][0]["claims"][0]["grounding_status"] = "blocked"
    result = validate_article_draft_quality(article_draft=value)
    assert result["checks"]["claim_evidence_grounding"] is False


def test_provisional_claim_is_not_publishable():
    value = _draft()
    value["sections"][0]["claims"][0]["grounding_status"] = "provisional"
    result = validate_article_draft_quality(article_draft=value)
    assert result["checks"]["claim_evidence_grounding"] is False


def test_duplicate_claim_evidence_refs_fail():
    value = _draft()
    value["sections"][0]["claims"][0]["evidence_refs"] = ["e1", "e1"]
    result = validate_article_draft_quality(article_draft=value)
    assert result["checks"]["claim_evidence_grounding"] is False
