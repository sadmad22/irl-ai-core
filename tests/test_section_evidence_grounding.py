from agents.research.section_evidence_grounding import ground_evidence_by_section


def _outline():
    return [
        {"heading": "Introduction", "purpose": "introduce the topic"},
        {"heading": "Costs and Pricing Factors", "purpose": "explain pricing factors"},
        {"heading": "Frequently Asked Questions", "purpose": "answer common questions"},
    ]


def _records():
    return [
        {
            "evidence_id": "ev_cost",
            "domain": "business",
            "claim": {"type": "business_value", "attribute": "pricing"},
            "value": {"type": "categorical", "data": "commercial"},
            "subject": {"type": "keyword", "id": "expat health insurance"},
            "source": {"artifact": "search-metrics.json"},
        },
        {
            "evidence_id": "ev_question",
            "domain": "question",
            "claim": {"type": "question", "attribute": "faq"},
            "value": {"type": "boolean", "data": True},
            "subject": {"type": "keyword", "id": "expat health insurance"},
            "source": {"artifact": "question-analysis.json"},
        },
        {
            "evidence_id": "ev_entity",
            "domain": "entity",
            "claim": {"type": "entity_presence", "attribute": "mentioned"},
            "value": {"type": "boolean", "data": True},
            "subject": {"type": "entity", "id": "example.org"},
            "source": {"artifact": "serp-analysis.json"},
        },
    ]


def test_grounding_rejects_internal_business_evidence_for_cost_section():
    result = ground_evidence_by_section(
        outline=_outline(),
        evidence_refs=["ev_cost", "ev_question", "ev_entity"],
        evidence_records=_records(),
        per_section=1,
    )

    assert result[1] == []


def test_grounding_is_deterministic_and_stays_within_lineage():
    kwargs = {
        "outline": _outline(),
        "evidence_refs": ["ev_cost", "ev_question", "ev_entity"],
        "evidence_records": _records(),
        "per_section": 2,
    }
    first = ground_evidence_by_section(**kwargs)
    second = ground_evidence_by_section(**kwargs)

    assert first == second
    assert all(ref in kwargs["evidence_refs"] for refs in first for ref in refs)
    assert first == second


def test_grounding_does_not_fallback_to_unrelated_evidence():
    outline = [
        {"heading": "Costs and Pricing Factors", "purpose": "explain pricing factors"},
    ]

    records = [
        {
            "evidence_id": "ev_business",
            "domain": "business",
            "claim": {"type": "business_value", "attribute": "pricing"},
            "value": {"type": "categorical", "data": "commercial"},
            "subject": {"type": "keyword", "id": "nurse insurance"},
            "source": {"artifact": "search-metrics.json"},
        },
        {
            "evidence_id": "ev_question",
            "domain": "question",
            "claim": {"type": "question", "attribute": "faq"},
            "value": {"type": "boolean", "data": True},
            "subject": {"type": "keyword", "id": "nurse insurance"},
            "source": {"artifact": "question-analysis.json"},
        },
    ]

    result = ground_evidence_by_section(
        outline=outline,
        evidence_refs=["ev_business", "ev_question"],
        evidence_records=records,
        per_section=2,
    )

    assert result == [[]]


def test_grounding_keeps_eligible_cost_evidence():
    outline = [
        {"heading": "Costs and Pricing Factors", "purpose": "explain pricing factors"},
    ]

    records = [
        {
            "evidence_id": "ev_premium",
            "domain": "market",
            "claim": {"type": "premium", "attribute": "pricing"},
            "value": {"type": "numeric", "data": 1200},
            "subject": {"type": "keyword", "id": "nurse insurance"},
            "source": {"artifact": "premium-analysis.json"},
        },
        {
            "evidence_id": "ev_business",
            "domain": "business",
            "claim": {"type": "business_value", "attribute": "pricing"},
            "value": {"type": "categorical", "data": "commercial"},
            "subject": {"type": "keyword", "id": "nurse insurance"},
            "source": {"artifact": "search-metrics.json"},
        },
    ]

    result = ground_evidence_by_section(
        outline=outline,
        evidence_refs=["ev_premium", "ev_business"],
        evidence_records=records,
        per_section=2,
    )

    assert result == [["ev_premium"]]



def test_compare_section_selects_relevant_evidence_from_substantive_value_text():
    outline = [
        {
            "heading": "How to Compare Options",
            "purpose": "compare policy coverage, benefits, and costs",
        },
    ]
    records = [
        {
            "evidence_id": "ev_policy_features",
            "domain": "substantive",
            "claim": {"type": "option_attribute", "attribute": "coverage_difference"},
            "value": {
                "type": "text",
                "data": (
                    "NSO individual nurse coverage includes portable coverage, "
                    "license defense expenses, and HIPAA-related supplementary benefits."
                ),
            },
            "subject": {"type": "insurance_product", "id": "NSO"},
            "source": {"artifact": "substantive-evidence.json"},
        },
        {
            "evidence_id": "ev_unrelated_topic",
            "domain": "substantive",
            "claim": {"type": "eligibility", "attribute": "who_needs_it"},
            "value": {
                "type": "text",
                "data": "Nurses work in clinical settings and may have different job duties.",
            },
            "subject": {"type": "profession", "id": "nurse"},
            "source": {"artifact": "source-material.json"},
        },
    ]

    result = ground_evidence_by_section(
        outline=outline,
        evidence_refs=["ev_policy_features", "ev_unrelated_topic"],
        evidence_records=records,
        per_section=4,
    )

    assert result == [["ev_policy_features"]]
