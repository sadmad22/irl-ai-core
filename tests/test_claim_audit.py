from agents.research.claim_audit import audit_article_claims, audit_claim


def _record(relation="supports"):
    return {
        "evidence_id": "e1",
        "domain": "cost",
        "claim": {"type": "pricing", "attribute": "premium"},
        "value": {"type": "text", "data": "Premium cost varies by age and coverage level."},
        "subject": {"type": "keyword", "id": "expat health insurance"},
        "relation": relation,
    }


def _claim(text="Premium cost varies by age and coverage level.", status="grounded", refs=None):
    return {
        "claim_id": "claim_1_1_test",
        "text": text,
        "evidence_refs": ["e1"] if refs is None else refs,
        "grounding_status": status,
    }


def test_supported_claim_passes():
    result = audit_claim(claim=_claim(), evidence_records=[_record()])
    assert result["result"] == "supported"
    assert result["evidence_refs"] == ["e1"]
    assert len(result["matched_tokens"]) >= 2


def test_unmatched_claim_is_insufficient():
    claim = _claim("Dental implants are always covered worldwide.")
    result = audit_claim(claim=claim, evidence_records=[_record()])
    assert result["result"] == "insufficient"
    assert result["evidence_refs"] == ["e1"]


def test_blocked_claim_is_insufficient():
    result = audit_claim(claim=_claim(status="blocked", refs=[]), evidence_records=[])
    assert result["result"] == "insufficient"


def test_contradictory_evidence_is_disputed():
    result = audit_claim(claim=_claim(), evidence_records=[_record("contradicts")])
    assert result["result"] == "disputed"


def test_article_audit_fails_closed_when_any_claim_is_not_supported():
    draft = {
        "draft_id": "draft_1",
        "sections": [{"claims": [_claim(), _claim("Dental implants are always covered worldwide.")]}],
    }
    result = audit_article_claims(article_draft=draft, evidence_records=[_record()])
    assert result["outcome"] == "needs_revision"
    assert result["counts"]["supported"] == 1
    assert result["counts"]["insufficient"] == 1
