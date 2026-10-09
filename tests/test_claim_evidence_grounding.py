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



def test_grounding_normalizes_portability_to_portable_coverage():
    record = {
        "evidence_id": "ev_portable",
        "domain": "substantive",
        "claim": {"type": "coverage_fact", "attribute": "coverage"},
        "value": {
            "type": "text",
            "data": (
                "NSO nurse malpractice coverage includes portable coverage, "
                "license defense expenses, and supplementary benefits."
            ),
        },
        "subject": {"type": "profession", "id": "nurse"},
    }
    section = [{
        "heading": "Coverage",
        "body": "Portability is another coverage characteristic identified in the sources.",
        "evidence_refs": ["ev_portable"],
    }]

    result = ground_claims_by_section(sections=section, evidence_records=[record])

    assert result[0][0]["grounding_status"] == "grounded"
    assert result[0][0]["evidence_refs"] == ["ev_portable"]


def test_grounding_normalizes_policy_forms_without_weakening_threshold():
    record = {
        "evidence_id": "ev_policy_form",
        "domain": "substantive",
        "claim": {"type": "coverage_fact", "attribute": "policy_form"},
        "value": {
            "type": "text",
            "data": (
                "Occurrence and claims-made policy forms are used in nurse malpractice coverage."
            ),
        },
        "subject": {"type": "profession", "id": "nurse"},
    }
    section = [{
        "heading": "Coverage and Key Factors",
        "body": "Policy form is a central distinction.",
        "evidence_refs": ["ev_policy_form"],
    }]

    result = ground_claims_by_section(sections=section, evidence_records=[record])

    assert result[0][0]["grounding_status"] == "grounded"
    assert result[0][0]["evidence_refs"] == ["ev_policy_form"]


def test_generic_comparison_advice_is_not_grounded_by_one_shared_word():
    record = {
        "evidence_id": "ev_coverage",
        "domain": "substantive",
        "claim": {"type": "coverage_fact", "attribute": "coverage"},
        "value": {
            "type": "text",
            "data": (
                "NSO lists professional liability coverage of up to $1 million per claim "
                "and $6 million annual aggregate, together with license defense expenses."
            ),
        },
        "subject": {"type": "profession", "id": "nurse"},
    }
    section = [{
        "heading": "How to Compare Options",
        "body": "Coverage details should also be compared.",
        "evidence_refs": ["ev_coverage"],
    }]

    result = ground_claims_by_section(sections=section, evidence_records=[record])

    assert result[0][0]["grounding_status"] == "blocked"
    assert result[0][0]["evidence_refs"] == []


def test_search_intent_fact_can_be_grounded_without_inferred_reader_behavior():
    record = {
        "evidence_id": "ev_intent_distribution",
        "domain": "intent",
        "claim": {"type": "serp_intent", "attribute": "intent_distribution"},
        "value": {
            "type": "distribution",
            "data": {"Informational": 0.7904, "Transactional": 0.2096},
        },
        "subject": {"type": "keyword", "id": "nurse insurance"},
    }
    section = [{
        "heading": "Introduction",
        "body": "The recorded search-intent distribution includes informational and transactional intent.",
        "evidence_refs": ["ev_intent_distribution"],
    }]

    result = ground_claims_by_section(sections=section, evidence_records=[record])

    assert result[0][0]["grounding_status"] == "grounded"
    assert result[0][0]["evidence_refs"] == ["ev_intent_distribution"]


def test_search_intent_does_not_ground_an_inference_about_reader_behavior():
    record = {
        "evidence_id": "ev_intent_distribution",
        "domain": "intent",
        "claim": {"type": "serp_intent", "attribute": "intent_distribution"},
        "value": {
            "type": "distribution",
            "data": {"Informational": 0.7904, "Transactional": 0.2096},
        },
        "subject": {"type": "keyword", "id": "nurse insurance"},
    }
    section = [{
        "heading": "Introduction",
        "body": (
            "It also identifies a smaller transactional component, meaning some readers "
            "may be researching providers or purchasing coverage."
        ),
        "evidence_refs": ["ev_intent_distribution"],
    }]

    result = ground_claims_by_section(sections=section, evidence_records=[record])

    assert result[0][0]["grounding_status"] == "blocked"
    assert result[0][0]["evidence_refs"] == []
