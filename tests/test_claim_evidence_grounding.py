from agents.research.claim_evidence_grounding import ground_claims_by_section


def _records():
    return [
        {"evidence_id": "ev_cost", "domain": "business", "claim": {"type": "business_value", "attribute": "pricing"}, "value": {"type": "categorical", "data": "premium"}, "subject": {"type": "keyword", "id": "insurance cost"}},
        {"evidence_id": "ev_entity", "domain": "entity", "claim": {"type": "entity_presence", "attribute": "provider"}, "value": {"type": "boolean", "data": True}, "subject": {"type": "entity", "id": "example provider"}},
    ]


def test_ground_claims_assigns_section_evidence():
    sections = [{"heading": "Costs", "body": "Insurance cost can vary by premium level.", "evidence_refs": ["ev_cost", "ev_entity"]}]
    result = ground_claims_by_section(sections=sections, evidence_records=_records())
    assert result[0][0]["grounding_status"] == "grounded"
    assert result[0][0]["evidence_refs"] == ["ev_cost"]
    assert result[0][0]["claim_id"].startswith("claim_1_1_")


def test_grounding_is_deterministic():
    sections = [{"heading": "Costs", "body": "Insurance cost can vary by premium level.", "evidence_refs": ["ev_cost", "ev_entity"]}]
    first = ground_claims_by_section(sections=sections, evidence_records=_records())
    second = ground_claims_by_section(sections=sections, evidence_records=_records())
    assert first == second


def test_unmatched_claim_is_blocked_not_invented():
    sections = [{"heading": "Costs", "body": "The moon affects insurance underwriting.", "evidence_refs": ["ev_cost"]}]
    result = ground_claims_by_section(sections=sections, evidence_records=_records())
    assert result[0][0]["grounding_status"] == "blocked"
    assert result[0][0]["evidence_refs"] == []


def test_claims_only_use_section_lineage():
    sections = [{"heading": "Costs", "body": "Insurance cost can vary by premium level.", "evidence_refs": ["ev_cost"]}]
    result = ground_claims_by_section(sections=sections, evidence_records=_records())
    assert set(result[0][0]["evidence_refs"]).issubset(set(sections[0]["evidence_refs"]))
